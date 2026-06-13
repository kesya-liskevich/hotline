from __future__ import annotations

import asyncio

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from scripts.broadcast_presession import SHEETS, menu_keyboard, unique_recipients


MESSAGE_TEXT = (
    "🔥 МАСТЕР-КЛАСС ОТ ROLLBAY — УЖЕ СЕГОДНЯ\n\n"
    "Команда Rollbay проведёт открытый мастер-класс по уходу за роликами и "
    "оборудованием.\n"
    "Расскажут:\n"
    "— как правильно обслуживать ролики;\n"
    "— какие детали требуют регулярного внимания;\n"
    "— как продлить срок службы оборудования;\n"
    "— каких ошибок в обслуживании стоит избегать.\n\n"
    "Полезно как новичкам, так и опытным райдерам — всегда есть пара вещей, "
    "которые помогают роликам служить дольше и работать лучше.\n\n"
    "📍 Street Sport Academy, 3 этаж, лекторий\n"
    "🕐 Сегодня, 13 июня, 13:00\n\n"
    "Ждём всех желающих!"
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
