from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Protocol

from hotline_bot.models import Registration
from hotline_bot.storage import HEADERS


class SheetsClient(Protocol):
    def append_registration(self, registration: Registration) -> None:
        ...

    def update_registration(self, registration: Registration) -> None:
        ...

    def spreadsheet_url(self) -> str:
        ...


class DriveClient(Protocol):
    async def upload_telegram_file(
        self,
        bot,
        file_id: str,
        registration: Registration,
        filename: str,
    ) -> str:
        ...


class NullSheetsClient:
    def append_registration(self, registration: Registration) -> None:
        return None

    def update_registration(self, registration: Registration) -> None:
        return None

    def spreadsheet_url(self) -> str:
        return "Google Sheets не настроен."


class NullDriveClient:
    async def upload_telegram_file(
        self,
        bot,
        file_id: str,
        registration: Registration,
        filename: str,
    ) -> str:
        return f"telegram:{file_id}"


class GoogleClients:
    def __init__(
        self,
        service_account_file: str | None,
        spreadsheet_id: str | None,
        drive_root_folder_id: str | None,
        drive_oauth_client_file: str | None = None,
        drive_oauth_token_file: str | None = None,
    ) -> None:
        self.service_account_file = service_account_file
        self.spreadsheet_id = spreadsheet_id
        self.drive_root_folder_id = drive_root_folder_id
        self.drive_oauth_client_file = drive_oauth_client_file
        self.drive_oauth_token_file = drive_oauth_token_file

    def sheets(self) -> SheetsClient:
        if not self.service_account_file or not self.spreadsheet_id:
            return NullSheetsClient()
        return GoogleSheetsClient(self.service_account_file, self.spreadsheet_id)

    def drive(self) -> DriveClient:
        if not self.service_account_file or not self.drive_root_folder_id:
            return NullDriveClient()
        return GoogleDriveClient(
            self.service_account_file,
            self.drive_root_folder_id,
            self.drive_oauth_client_file,
            self.drive_oauth_token_file,
        )


class GoogleSheetsClient:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

    def __init__(self, service_account_file: str, spreadsheet_id: str) -> None:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        credentials = service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=self.SCOPES,
        )
        self.spreadsheet_id = spreadsheet_id
        self.service = build("sheets", "v4", credentials=credentials)
        self._ensure_headers()

    def append_registration(self, registration: Registration) -> None:
        body = {"values": [registration.as_row()]}
        for sheet_name in ("registrations_all", "competitions"):
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A:S",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body=body,
            ).execute()

    def update_registration(self, registration: Registration) -> None:
        # Append-only history is safer for the first MVP. The latest row by
        # registration_id/status is the source of truth for manual reporting.
        self.append_registration(registration)

    def spreadsheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    def _ensure_headers(self) -> None:
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        existing_titles = {
            sheet["properties"]["title"]
            for sheet in spreadsheet.get("sheets", [])
        }
        missing = [
            title
            for title in ("registrations_all", "competitions", "summary")
            if title not in existing_titles
        ]
        if missing:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id,
                body={
                    "requests": [
                        {"addSheet": {"properties": {"title": title}}}
                        for title in missing
                    ]
                },
            ).execute()
        for sheet_name in ("registrations_all", "competitions", "summary"):
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:S1",
                valueInputOption="RAW",
                body={"values": [HEADERS]},
            ).execute()


class GoogleDriveClient:
    SCOPES = ["https://www.googleapis.com/auth/drive.file"]

    def __init__(
        self,
        service_account_file: str,
        root_folder_id: str,
        oauth_client_file: str | None = None,
        oauth_token_file: str | None = None,
    ) -> None:
        from googleapiclient.discovery import build

        credentials = self._credentials(
            service_account_file,
            oauth_client_file,
            oauth_token_file,
        )
        self.root_folder_id = root_folder_id
        self.service = build("drive", "v3", credentials=credentials)

    def _credentials(
        self,
        service_account_file: str,
        oauth_client_file: str | None,
        oauth_token_file: str | None,
    ):
        oauth_token = Path(oauth_token_file) if oauth_token_file else None
        if oauth_token and oauth_token.exists():
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request

            credentials = Credentials.from_authorized_user_file(str(oauth_token), self.SCOPES)
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                oauth_token.write_text(credentials.to_json(), encoding="utf-8")
            return credentials

        from google.oauth2 import service_account

        return service_account.Credentials.from_service_account_file(
            service_account_file,
            scopes=self.SCOPES,
        )

    async def upload_telegram_file(
        self,
        bot,
        file_id: str,
        registration: Registration,
        filename: str,
    ) -> str:
        from googleapiclient.http import MediaFileUpload

        try:
            folder_id = self._ensure_registration_folder(registration)
            telegram_file = await bot.get_file(file_id)
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / filename
                await bot.download_file(telegram_file.file_path, destination=path)
                media = MediaFileUpload(str(path), resumable=False)
                uploaded = self.service.files().create(
                    body={"name": filename, "parents": [folder_id]},
                    media_body=media,
                    fields="id, webViewLink",
                ).execute()
            return uploaded.get("webViewLink") or f"https://drive.google.com/file/d/{uploaded['id']}/view"
        except Exception as exc:
            print(f"Google Drive upload failed, keeping Telegram file_id: {exc}")
            return f"telegram:{file_id}"

    def _ensure_registration_folder(self, registration: Registration) -> str:
        folder_name = f"{registration.full_name} - {registration.telegram_id} - {registration.registration_id}"
        safe_folder_name = folder_name.replace("\\", "\\\\").replace("'", "\\'")
        query = (
            f"name = '{safe_folder_name}' and "
            f"'{self.root_folder_id}' in parents and "
            "mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        )
        result = self.service.files().list(q=query, fields="files(id)").execute()
        files = result.get("files", [])
        if files:
            return files[0]["id"]
        folder = self.service.files().create(
            body={
                "name": folder_name,
                "parents": [self.root_folder_id],
                "mimeType": "application/vnd.google-apps.folder",
            },
            fields="id",
        ).execute()
        return folder["id"]
