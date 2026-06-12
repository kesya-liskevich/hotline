from __future__ import annotations

import asyncio

from aiogram import Bot

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.kevin_groups import grouped_participants
from hotline_bot.keyboards import kevin_group_attendance_keyboard


MESSAGE_TEXT = (
    "👁 Привет! Это «Горячая линия» роллерблейдинга\n\n"
    "Зовём тебя на бесплатный мастер-класс с Kevin Lee 🇰🇷\n\n"
    "Мы решили немного изменить формат и пригласить всех зарегистрировавшихся, "
    "разделив участников на две группы: PRO и Beginner.\n\n"
    "🔥 Ты попал в группу PRO\n\n"
    "📍 Место:\n"
    "Street Sport Academy\n"
    "Автовская, 31Б, м. Кировский завод\n\n"
    "🕕 Время:\n"
    "Суббота, 13 июня, 18:00\n\n"
    "Что взять с собой:\n"
    "— ролики;\n"
    "— защиту.\n\n"
    "Тренировка будет ориентирована на райдеров с опытом катания, поэтому Kevin сможет "
    "уделить больше внимания технике, связкам, работе на фигурах и индивидуальным "
    "рекомендациям.\n\n"
    "✅ Если придёте, нажмите кнопку «Приду»\n"
    "❌ Если прийти не получится, пожалуйста, нажмите кнопку «Не смогу прийти»"
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
    recipients, _, missing = grouped_participants(sheets.kevin_lottery_rows())
    if missing:
        raise RuntimeError(f"Kevin Lee group members missing from sheet: {missing}")
    print(f"PRO recipients: {len(recipients)}")

    bot = Bot(settings.bot_token)
    sent = 0
    failed = 0
    try:
        for recipient in recipients:
            try:
                await bot.send_message(
                    recipient.telegram_id,
                    MESSAGE_TEXT,
                    reply_markup=kevin_group_attendance_keyboard("pro"),
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
