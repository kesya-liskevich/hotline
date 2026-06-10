from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.models import Registration, RegistrationStatus


def _file_references(value: str) -> list[str]:
    return [item.strip() for item in value.splitlines() if item.strip()]


async def _recover_field(
    bot: Bot,
    drive,
    registration: Registration,
    value: str,
    filename_prefix: str,
) -> tuple[str, int]:
    recovered = 0
    updated_references: list[str] = []
    for index, reference in enumerate(_file_references(value), start=1):
        if not reference.startswith("telegram:"):
            updated_references.append(reference)
            continue
        file_id = reference.removeprefix("telegram:")
        filename = f"{filename_prefix}_{index}.jpg"
        uploaded_url = await drive.upload_telegram_file(
            bot,
            file_id,
            registration,
            filename,
        )
        if uploaded_url.startswith("telegram:"):
            raise RuntimeError(
                f"Could not recover {filename_prefix} for registration "
                f"{registration.registration_id}"
            )
        updated_references.append(uploaded_url)
        recovered += 1
    return "\n".join(updated_references), recovered


async def main() -> None:
    settings = get_settings()
    google = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    )
    sheets = google.sheets()
    drive = google.drive()
    registrations = sheets.list_registrations_with_telegram_files()
    bot = Bot(settings.bot_token)
    recovered_files = 0
    recovered_registrations = 0
    try:
        for registration in registrations:
            passport_url, passport_count = await _recover_field(
                bot,
                drive,
                registration,
                registration.passport_file_url,
                "passport",
            )
            consent_url, consent_count = await _recover_field(
                bot,
                drive,
                registration,
                registration.consent_file_url,
                "signed_document",
            )
            registration.passport_file_url = passport_url
            registration.consent_file_url = consent_url
            registration.updated_at = datetime.now(timezone.utc).isoformat()
            sheets.update_registration(registration)
            recovered_files += passport_count + consent_count
            recovered_registrations += 1
            print(
                f"Recovered registration {registration.registration_id}: "
                f"{passport_count + consent_count} file(s)"
            )
    finally:
        await bot.session.close()
    print(
        f"Recovery complete: {recovered_files} file(s), "
        f"{recovered_registrations} registration(s)"
    )


if __name__ == "__main__":
    asyncio.run(main())
