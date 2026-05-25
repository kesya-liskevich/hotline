from __future__ import annotations

from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleDriveClient


def main() -> None:
    settings = get_settings()
    if not settings.google_drive_oauth_client_file:
        raise SystemExit("Set GOOGLE_DRIVE_OAUTH_CLIENT_FILE in .env first.")

    client_file = Path(settings.google_drive_oauth_client_file)
    if not client_file.exists():
        raise SystemExit(f"OAuth client file not found: {client_file}")

    flow = InstalledAppFlow.from_client_secrets_file(
        str(client_file),
        scopes=GoogleDriveClient.SCOPES,
    )
    credentials = flow.run_local_server(port=0)
    token_file = Path(settings.google_drive_oauth_token_file)
    token_file.write_text(credentials.to_json(), encoding="utf-8")
    print(f"Saved Google Drive OAuth token to {token_file}")


if __name__ == "__main__":
    main()

