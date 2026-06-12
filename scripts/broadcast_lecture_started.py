from __future__ import annotations

import asyncio

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from scripts.broadcast_presession import SHEETS, menu_keyboard, unique_recipients


MESSAGE_TEXT = (
    "Лекция «Профилактика травм в экстремальном спорте» уже началась!\n\n"
    "📍 Ждём вас на 3 этаже в лектории.\n\n"
    "Говорим о том, как кататься дольше, прогрессировать безопаснее и избегать "
    "самых частых травм.\n"
    "Присоединяйтесь🔥"
)


async def main() -> None:
    settings = get_settings()
    sheets = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    ).sheets()
    rows_by_sheet = {
        sheet_name: sheets._read_rows(f"{sheet_name}!A2:Z")
        for sheet_name in SHEETS
    }
    recipients = unique_recipients(rows_by_sheet)
    print(f"Unique recipients: {len(recipients)}")

    bot = Bot(settings.bot_token)
    sent = 0
    failed = 0
    try:
        for recipient in recipients:
            try:
                await bot.send_message(
                    recipient.telegram_id,
                    MESSAGE_TEXT,
                    reply_markup=menu_keyboard(),
                )
                sent += 1
                await asyncio.sleep(0.05)
            except Exception as exc:
                failed += 1
                print(f"Failed for {recipient.telegram_id}: {exc}")
    finally:
        await bot.session.close()
    print(f"Delivered: {sent}/{len(recipients)}; failed: {failed}")


if __name__ == "__main__":
    asyncio.run(main())
