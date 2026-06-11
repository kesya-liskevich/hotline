from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path
import sys

from aiogram import Bot
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients


IMAGE_PATH = PROJECT_ROOT / "assets" / "presession_broadcast.png"
DEFAULT_TEST_USERNAMES = ("kesyaliskevich", "Because_why_not")
SHEETS = {
    "competitions": (1, 2),
    "workshops": (1, 2),
    "kevin_lee": (1, 2),
    "kevin_lee_lottery": (1, 2),
    "kevin_lee_paid": (1, 2),
}
MESSAGE_TEXT = (
    "🔥<b>ВСЕМ ЙОУ! СЕГОДНЯ ПРЕСЕЙШН</b>\n\n"
    "Сегодня встречаемся на первом большом общем катании «Горячей линии» перед контестом.\n\n"
    "<b>В программе:</b>\n"
    "— Джем-сессия на рейл-боксе\n"
    "— Джем-сессия в бетонном боуле\n"
    "— Eazy Money\n"
    "— Женский джем в рампе\n"
    "— Best Tricks с призами\n\n"
    "👁️ Вход свободный. Всем быть!\n\n"
    "Это отличный повод раскататься перед соревнованиями, познакомиться с участниками "
    "и просто классно провести вечер.\n\n"
    '📍 <a href="https://yandex.ru/maps/-/CPw87HyL">Скейт-парк под мостом Бетанкура</a>\n'
    "🕕 Сбор в 18:00\n\n"
    "Важная просьба: пожалуйста, не мажьте копинги в боуле парафином. "
    "Если нужно — мажьте только свои ролики.\n\n"
    "До встречи вечером!"
)


@dataclass(frozen=True)
class Recipient:
    telegram_id: int
    telegram_username: str | None = None


def unique_recipients(
    rows_by_sheet: dict[str, list[list[str]]],
    usernames: set[str] | None = None,
) -> list[Recipient]:
    normalized_usernames = {value.lstrip("@").lower() for value in usernames or set()}
    recipients: dict[int, Recipient] = {}
    for sheet_name, rows in rows_by_sheet.items():
        id_index, username_index = SHEETS[sheet_name]
        for row in rows:
            try:
                telegram_id = int(row[id_index])
            except (IndexError, TypeError, ValueError):
                continue
            username = row[username_index].strip() if len(row) > username_index else ""
            if normalized_usernames and username.lstrip("@").lower() not in normalized_usernames:
                continue
            current = recipients.get(telegram_id)
            if current is None or (not current.telegram_username and username):
                recipients[telegram_id] = Recipient(telegram_id, username or None)
    return sorted(recipients.values(), key=lambda item: item.telegram_id)


def menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="В меню", callback_data="menu")],
        ]
    )


async def run(send: bool, usernames: set[str] | None) -> None:
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
    recipients = unique_recipients(rows_by_sheet, usernames)

    print(f"Unique recipients: {len(recipients)}")
    if not send:
        print("Dry run only. Add --send to deliver the broadcast.")
        return
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Broadcast image not found: {IMAGE_PATH}")

    bot = Bot(settings.bot_token)
    sent = 0
    failed = 0
    try:
        for recipient in recipients:
            try:
                await bot.send_photo(recipient.telegram_id, FSInputFile(IMAGE_PATH))
                await bot.send_message(
                    recipient.telegram_id,
                    MESSAGE_TEXT,
                    parse_mode="HTML",
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send the festival presession broadcast.")
    parser.add_argument("--send", action="store_true", help="Actually send messages.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Send to every unique Telegram ID instead of the test accounts.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    target_usernames = None if args.all else set(DEFAULT_TEST_USERNAMES)
    asyncio.run(run(args.send, target_usernames))
