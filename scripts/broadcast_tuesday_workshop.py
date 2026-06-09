from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from aiogram import Bot
from aiogram.types import FSInputFile

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.keyboards import workshop_attendance_keyboard
from scripts.broadcast_monday_workshop import active_recipients


WORKSHOP_ID = "tue_ofp"
IMAGE_PATH = PROJECT_ROOT / "assets" / "workshop_tuesday_location_update.png"
MESSAGE_TEXT = (
    "⚠️ <b>Важное обновление по мастер-классу 9 июня</b>\n\n"
    "Из-за погодных условий мастер-класс «ОФП и подготовка тела к катанию» с Егором "
    "Логиновым переносится на другую площадку.\n\n"
    "📍 <b>Новая локация:</b>\n"
    "Street Sport Academy\n"
    "Автозаводская, 31Б\n\n"
    "🕕 Время без изменений — 18:00\n\n"
    "Не переживайте, программа мастер-класса остаётся прежней. Ждём вас сегодня в 18:00, "
    "просто по новому адресу.\n\n"
    "<b>Что будет:</b>\n"
    "— тренировка по общей физической подготовке для роллеров;\n"
    "— работа над физической базой, которая помогает прогрессировать в катании и снижать "
    "риск травм.\n\n"
    "<b>Что взять с собой:</b>\n"
    "— удобную спортивную одежду;\n"
    "— чистую сменную обувь;\n"
    "❗️Ролики для занятия не понадобятся.\n\n"
    "Все места на мастер-класс уже заняты, регистрация закрыта.\n\n"
    "До встречи сегодня в Street Sport Academy 👊"
)


async def run(send: bool) -> None:
    settings = get_settings()
    sheets = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    ).sheets()
    recipients = active_recipients(sheets.list_workshop_registrations(WORKSHOP_ID))

    print(f"Recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"- @{recipient.telegram_username}: {recipient.telegram_id}")
    if not send:
        print("Dry run only. Add --send to deliver the update.")
        return
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Broadcast image not found: {IMAGE_PATH}")

    bot = Bot(settings.bot_token)
    sent = 0
    try:
        for recipient in recipients:
            try:
                await bot.send_photo(recipient.telegram_id, FSInputFile(IMAGE_PATH))
                await bot.send_message(
                    recipient.telegram_id,
                    MESSAGE_TEXT,
                    parse_mode="HTML",
                    reply_markup=workshop_attendance_keyboard(WORKSHOP_ID),
                )
                sent += 1
                print(f"Sent to @{recipient.telegram_username}: {recipient.telegram_id}")
            except Exception as exc:
                print(f"Failed for @{recipient.telegram_username}: {recipient.telegram_id}: {exc}")
    finally:
        await bot.session.close()
    print(f"Delivered: {sent}/{len(recipients)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send the Tuesday workshop location update.")
    parser.add_argument("--send", action="store_true", help="Actually send messages.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.send))
