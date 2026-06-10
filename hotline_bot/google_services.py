from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

from hotline_bot.models import KevinTrainingRegistration, Registration, RegistrationStatus, WorkshopRegistration
from hotline_bot.storage import HEADERS, KEVIN_TRAINING_HEADERS, WORKSHOP_HEADERS


class SheetsClient(Protocol):
    def append_registration(self, registration: Registration) -> None:
        ...

    def append_workshop_registration(self, registration: WorkshopRegistration) -> None:
        ...

    def append_kevin_training_registration(self, registration: KevinTrainingRegistration) -> None:
        ...

    def update_workshop_registration(self, registration: WorkshopRegistration) -> None:
        ...

    def list_registrations_by_user(self, telegram_id: int) -> list[Registration]:
        ...

    def list_registrations_with_telegram_files(self) -> list[Registration]:
        ...

    def list_workshop_registrations_by_user(self, telegram_id: int) -> list[WorkshopRegistration]:
        ...

    def list_workshop_registrations(self, workshop_id: str) -> list[WorkshopRegistration]:
        ...

    def append_workshop_attendance(
        self,
        workshop_id: str,
        telegram_id: int,
        telegram_username: str | None,
        full_name: str,
        response: str,
    ) -> None:
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

    def append_workshop_registration(self, registration: WorkshopRegistration) -> None:
        return None

    def append_kevin_training_registration(self, registration: KevinTrainingRegistration) -> None:
        return None

    def update_workshop_registration(self, registration: WorkshopRegistration) -> None:
        return None

    def list_registrations_by_user(self, telegram_id: int) -> list[Registration]:
        return []

    def list_registrations_with_telegram_files(self) -> list[Registration]:
        return []

    def list_workshop_registrations_by_user(self, telegram_id: int) -> list[WorkshopRegistration]:
        return []

    def list_workshop_registrations(self, workshop_id: str) -> list[WorkshopRegistration]:
        return []

    def append_workshop_attendance(
        self,
        workshop_id: str,
        telegram_id: int,
        telegram_username: str | None,
        full_name: str,
        response: str,
    ) -> None:
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

    def append_workshop_registration(self, registration: WorkshopRegistration) -> None:
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range="workshops!A:M",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [registration.as_row()]},
        ).execute()

    def append_kevin_training_registration(self, registration: KevinTrainingRegistration) -> None:
        sheet_name = "kevin_lee_paid" if registration.participation_type == "paid" else "kevin_lee_lottery"
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A:K",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [registration.as_row()]},
        ).execute()

    def update_workshop_registration(self, registration: WorkshopRegistration) -> None:
        self.append_workshop_registration(registration)

    def list_registrations_by_user(self, telegram_id: int) -> list[Registration]:
        rows = self._read_rows("competitions!A2:S")
        latest: dict[str, Registration] = {}
        for row in rows:
            registration = _registration_from_sheet_row(row)
            if registration and registration.telegram_id == telegram_id:
                latest[registration.registration_id] = registration
        return sorted(latest.values(), key=lambda item: item.created_at, reverse=True)

    def list_registrations_with_telegram_files(self) -> list[Registration]:
        rows = self._read_rows("competitions!A2:S")
        latest: dict[str, Registration] = {}
        for row in rows:
            registration = _registration_from_sheet_row(row)
            if registration:
                latest[registration.registration_id] = registration
        return [
            registration
            for registration in latest.values()
            if registration.status == RegistrationStatus.SUBMITTED
            and (
                "telegram:" in registration.passport_file_url
                or "telegram:" in registration.consent_file_url
            )
        ]

    def list_workshop_registrations_by_user(self, telegram_id: int) -> list[WorkshopRegistration]:
        rows = self._read_rows("workshops!A2:M")
        latest: dict[str, WorkshopRegistration] = {}
        for row in rows:
            registration = _workshop_registration_from_sheet_row(row)
            if registration and registration.telegram_id == telegram_id:
                latest[registration.registration_id] = registration
        return sorted(latest.values(), key=lambda item: item.created_at, reverse=True)

    def list_workshop_registrations(self, workshop_id: str) -> list[WorkshopRegistration]:
        rows = self._read_rows("workshops!A2:M")
        latest: dict[str, WorkshopRegistration] = {}
        for row in rows:
            registration = _workshop_registration_from_sheet_row(row)
            if registration and registration.workshop_id == workshop_id:
                latest[registration.registration_id] = registration
        return sorted(latest.values(), key=lambda item: item.created_at, reverse=True)

    def append_workshop_attendance(
        self,
        workshop_id: str,
        telegram_id: int,
        telegram_username: str | None,
        full_name: str,
        response: str,
    ) -> None:
        self.service.spreadsheets().values().append(
            spreadsheetId=self.spreadsheet_id,
            range="workshop_attendance!A:F",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={
                "values": [[
                    workshop_id,
                    str(telegram_id),
                    telegram_username or "",
                    full_name,
                    response,
                    datetime.now(timezone.utc).isoformat(),
                ]]
            },
        ).execute()

    def update_registration(self, registration: Registration) -> None:
        # Append-only history is safer for the first MVP. The latest row by
        # registration_id/status is the source of truth for manual reporting.
        self.append_registration(registration)

    def spreadsheet_url(self) -> str:
        return f"https://docs.google.com/spreadsheets/d/{self.spreadsheet_id}"

    def _read_rows(self, range_name: str) -> list[list[str]]:
        result = self.service.spreadsheets().values().get(
            spreadsheetId=self.spreadsheet_id,
            range=range_name,
        ).execute()
        return result.get("values", [])

    def _ensure_headers(self) -> None:
        spreadsheet = self.service.spreadsheets().get(spreadsheetId=self.spreadsheet_id).execute()
        existing_titles = {
            sheet["properties"]["title"]
            for sheet in spreadsheet.get("sheets", [])
        }
        missing = [
            title
            for title in (
                "registrations_all",
                "competitions",
                "summary",
                "workshops",
                "kevin_lee",
                "kevin_lee_lottery",
                "kevin_lee_paid",
                "workshop_attendance",
            )
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
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="workshops!A1:M1",
            valueInputOption="RAW",
            body={"values": [WORKSHOP_HEADERS]},
        ).execute()
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="kevin_lee!A1:K1",
            valueInputOption="RAW",
            body={"values": [KEVIN_TRAINING_HEADERS]},
        ).execute()
        for sheet_name in ("kevin_lee_lottery", "kevin_lee_paid"):
            self.service.spreadsheets().values().update(
                spreadsheetId=self.spreadsheet_id,
                range=f"{sheet_name}!A1:K1",
                valueInputOption="RAW",
                body={"values": [KEVIN_TRAINING_HEADERS]},
            ).execute()
        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range="workshop_attendance!A1:F1",
            valueInputOption="RAW",
            body={
                "values": [[
                    "workshop_id",
                    "telegram_id",
                    "telegram_username",
                    "full_name",
                    "response",
                    "responded_at",
                ]]
            },
        ).execute()
        self._migrate_legacy_kevin_lottery_rows()

    def _migrate_legacy_kevin_lottery_rows(self) -> None:
        legacy_rows = self._read_rows("kevin_lee!A2:K")
        lottery_rows = self._read_rows("kevin_lee_lottery!A2:K")
        existing_ids = {_cell(row, 0) for row in lottery_rows}
        rows_to_copy: list[list[str]] = []
        for row in legacy_rows:
            registration_id = _cell(row, 0)
            if not registration_id or registration_id in existing_ids:
                continue
            padded = [*row, *[""] * (len(KEVIN_TRAINING_HEADERS) - len(row))]
            if len(row) == 10:
                padded = [*row[:7], "lottery", *row[7:]]
            padded[6] = padded[6] or "kevin_lee_training"
            padded[7] = padded[7] or "lottery"
            rows_to_copy.append(padded[: len(KEVIN_TRAINING_HEADERS)])
        if rows_to_copy:
            self.service.spreadsheets().values().append(
                spreadsheetId=self.spreadsheet_id,
                range="kevin_lee_lottery!A:K",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": rows_to_copy},
            ).execute()


def _cell(row: list[str], index: int) -> str:
    return row[index] if len(row) > index else ""


def _registration_from_sheet_row(row: list[str]) -> Registration | None:
    try:
        registration = Registration(
            registration_id=_cell(row, 0),
            telegram_id=int(_cell(row, 1)),
            telegram_username=_cell(row, 2) or None,
            full_name=_cell(row, 3),
            phone=_cell(row, 4),
            city=_cell(row, 5),
            discipline=_cell(row, 7),
            category=_cell(row, 8),
            age_or_birthdate=_cell(row, 9),
            experience=_cell(row, 10),
            sponsors=_cell(row, 11),
            passport_file_url=_cell(row, 12),
            consent_file_url=_cell(row, 13),
            status=RegistrationStatus(_cell(row, 14) or RegistrationStatus.SUBMITTED.value),
            needs_review=_cell(row, 15).lower() == "yes",
            review_note=_cell(row, 16),
            created_at=_cell(row, 17),
            updated_at=_cell(row, 18),
        )
    except (TypeError, ValueError):
        return None
    return registration if registration.registration_id else None


def _workshop_registration_from_sheet_row(row: list[str]) -> WorkshopRegistration | None:
    try:
        registration = WorkshopRegistration(
            registration_id=_cell(row, 0),
            telegram_id=int(_cell(row, 1)),
            telegram_username=_cell(row, 2) or None,
            full_name=_cell(row, 3),
            phone=_cell(row, 4),
            workshop_id=_cell(row, 6),
            workshop_title=_cell(row, 7),
            workshop_date=_cell(row, 8),
            skating_type=_cell(row, 9),
            status=RegistrationStatus(_cell(row, 10) or RegistrationStatus.SUBMITTED.value),
            created_at=_cell(row, 11),
            updated_at=_cell(row, 12),
        )
    except (TypeError, ValueError):
        return None
    return registration if registration.registration_id else None


class GoogleDriveClient:
    SCOPES = ["https://www.googleapis.com/auth/drive"]

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

            try:
                credentials = Credentials.from_authorized_user_file(str(oauth_token), self.SCOPES)
                if credentials.expired and credentials.refresh_token:
                    credentials.refresh(Request())
                    try:
                        oauth_token.write_text(credentials.to_json(), encoding="utf-8")
                    except OSError as exc:
                        print(f"Could not persist refreshed Google Drive token: {exc}")
                return credentials
            except Exception as exc:
                print(f"Could not use Google Drive OAuth token, falling back to service account: {exc}")

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
