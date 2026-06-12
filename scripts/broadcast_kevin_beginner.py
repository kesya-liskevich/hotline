from __future__ import annotations

import argparse
import asyncio

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.kevin_groups import grouped_participants
from hotline_bot.keyboards import kevin_group_attendance_keyboard
from scripts.broadcast_presession import (
    DEFAULT_TEST_USERNAMES,
    SHEETS,
    unique_recipients,
)


MESSAGE_TEXT = (
    "👁 Привет! Это «Горячая линия» роллерблейдинга\n\n"
    "Зовём тебя на бесплатный мастер-класс с Kevin Lee 🇰🇷\n\n"
    "Мы решили немного изменить формат и пригласить всех зарегистрировавшихся, "
    "разделив участников на две группы: PRO и Beginner.\n\n"
    "🔥 Ты попал в группу Beginner\n\n"
    "📍 Место:\n"
    "Street Sport Academy\n"
    "Автовская, 31Б, м. Кировский завод\n\n"
    "🕕 Время: воскресенье, 14 июня, 9:30\n\n"
    "Что взять с собой:\n"
    "— ролики;\n"
    "— защиту.\n\n"
    "Тренировка подойдёт для начинающих райдеров и тех, кто хочет увереннее чувствовать "
    "себя в скейт-парке. Kevin поможет разобраться с базовыми навыками, подскажет, над "
    "чем стоит поработать дальше, и ответит на вопросы участников.\n\n"
    "Не переживай, если пока не умеешь сложные трюки — этот мастер-класс как раз для "
    "того, чтобы учиться новому и прогрессировать в комфортной атмосфере 🤝\n\n"
    "✅ Если придёте, нажмите кнопку «Приду»\n"
    "❌ Если прийти не получится, пожалуйста, нажмите кнопку «Не смогу прийти»"
)


async def run(send: bool, send_all: bool) -> None:
    settings = get_settings()
    sheets = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    ).sheets()
    if send_all:
        _, recipients, missing = grouped_participants(sheets.kevin_lottery_rows())
        if missing:
            raise RuntimeError(f"Kevin Lee group members missing from sheet: {missing}")
    else:
        rows_by_sheet = {
            sheet_name: sheets._read_rows(f"{sheet_name}!A2:Z")
            for sheet_name in SHEETS
        }
        recipients = unique_recipients(
            rows_by_sheet,
            set(DEFAULT_TEST_USERNAMES),
        )

    print(f"Recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"- {recipient.telegram_id}: {recipient.telegram_username}")
    if not send:
        print("Dry run only. Add --send to deliver the test.")
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
                    reply_markup=kevin_group_attendance_keyboard("beginner"),
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
    parser = argparse.ArgumentParser(description="Send the Kevin Lee Beginner group invitation.")
    parser.add_argument("--send", action="store_true", help="Actually send messages.")
    parser.add_argument("--all", action="store_true", help="Send to all Beginner participants.")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.send, args.all))
