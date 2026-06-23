from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from scripts.broadcast_presession import menu_keyboard


ATTENDANCE_SHEETS = (
    "kevin_lee_beginner_attendance",
    "kevin_lee_pro_attendance",
)
MESSAGE_TEXT = (
    "👁 Спасибо, что участвовали в мастер-классах Kevin Lee 🇰🇷\n\n"
    "Кевин просил поделиться впечатлениями о тренировках, а нам очень важно "
    "собрать вашу обратную связь, чтобы сделать будущие мероприятия ещё лучше.\n\n"
    "Чтобы оставить отзыв:\n"
    "— нажмите /start или введите команду вручную;\n"
    "— выберите в меню кнопку «Обратная связь»;\n"
    "— ответьте на несколько вопросов.\n\n"
    "Спасибо за участие и поддержку «Горячей линии» 🔥"
)


@dataclass(frozen=True)
class Recipient:
    telegram_id: int
    telegram_username: str | None = None
    full_name: str = ""


def confirmed_recipients(rows_by_sheet: dict[str, list[list[str]]]) -> list[Recipient]:
    recipients: dict[int, Recipient] = {}
    for rows in rows_by_sheet.values():
        for row in rows:
            response = _cell(row, 4).strip().lower()
            is_test = _cell(row, 5).strip().lower()
            if response != "yes" or is_test == "yes":
                continue
            try:
                telegram_id = int(_cell(row, 1))
            except ValueError:
                continue
            username = _cell(row, 2).strip() or None
            full_name = _cell(row, 3).strip()
            current = recipients.get(telegram_id)
            if current is None or (not current.telegram_username and username):
                recipients[telegram_id] = Recipient(telegram_id, username, full_name)
    return sorted(recipients.values(), key=lambda item: item.telegram_id)


async def run(send: bool) -> None:
    settings = get_settings()
    sheets = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    ).sheets()
    rows_by_sheet = {
        sheet_name: sheets._read_rows(f"{sheet_name}!A2:G")
        for sheet_name in ATTENDANCE_SHEETS
    }
    recipients = confirmed_recipients(rows_by_sheet)

    print(f"Confirmed Kevin Lee recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"- {recipient.telegram_id}: {recipient.telegram_username or ''} {recipient.full_name}")
    if not send:
        print("Dry run only. Add --send to deliver the broadcast.")
        return

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


def _cell(row: list[str], index: int) -> str:
    return row[index] if len(row) > index else ""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send Kevin Lee feedback request.")
    parser.add_argument("--send", action="store_true", help="Actually send messages.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.send))
