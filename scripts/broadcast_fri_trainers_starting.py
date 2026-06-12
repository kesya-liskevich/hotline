from __future__ import annotations

import asyncio

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from scripts.broadcast_monday_workshop import active_recipients
from scripts.broadcast_presession import menu_keyboard


WORKSHOP_ID = "fri_trainers"
MESSAGE_TEXT = (
    "🚨 Через 15 минут начинается воркшоп с Kevin Lee!\n\n"
    "Встречаемся в лектории на 3 этаже Street Sport Academy.\n"
    "🕒 Сбор в 18:00\n\n"
    "Подходите заранее, чтобы мы успели собрать группу и начать вовремя.\n"
    "До встречи!"
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
    recipients = active_recipients(
        sheets.list_workshop_registrations(WORKSHOP_ID),
    )
    print(f"Active unique recipients: {len(recipients)}")

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
