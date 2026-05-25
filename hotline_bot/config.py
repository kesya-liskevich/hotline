from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str
    admin_ids: str = ""
    database_path: str = "hotline.sqlite3"
    google_service_account_file: str | None = None
    google_sheets_spreadsheet_id: str | None = None
    google_drive_root_folder_id: str | None = None
    google_drive_oauth_client_file: str | None = None
    google_drive_oauth_token_file: str = "google-drive-token.json"
    consent_document_file_id: str | None = None

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def admin_id_set(self) -> set[int]:
        ids: set[int] = set()
        for item in self.admin_ids.split(","):
            item = item.strip()
            if item:
                ids.add(int(item))
        return ids


@lru_cache
def get_settings() -> Settings:
    return Settings()
