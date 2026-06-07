from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

from aiogram import Bot
from aiogram.types import FSInputFile, LinkPreviewOptions

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.models import RegistrationStatus, WorkshopRegistration


WORKSHOP_ID = "mon_fsk_aggressive"
DEFAULT_TEST_USERNAMES = ("kesyaliskevich", "Because_why_not")
IMAGE_PATH = PROJECT_ROOT / "assets" / "workshop_mon_reminder.png"
MESSAGE_TEXT = (
    "Привет! Это «Горячая линия» 👁️\n"
    "Напоминаем, что уже завтра, 8 июня, состоится мастер-класс:\n\n"
    "🔥 <b>Как подготовить своё катание от FSK к агрессивным роликам</b>\n\n"
    "Большая открытая тренировка от тренеров Street Sport Academy подойдёт как тем, "
    "кто только хочет попробовать агрессивное катание, так и райдерам, которые уже "
    "катаются в FSK и хотят прокачать свои навыки.\n\n"
    "На тренировке разберём:\n"
    "— базовые упражнения для уверенного контроля роликов;\n"
    "— технику прохождения фигур в скейт-парке;\n"
    "— переход от городского катания к агрессивному стилю;\n"
    "— навыки, которые пригодятся любому роллеру независимо от дисциплины.\n\n"
    "📍 Скейт-парк на набережной Макарова\n"
    'Адрес: <a href="https://yandex.ru/maps/org/180794722258?si=tyk0raf48ebpb33bmby3m4v9wm">'
    "напротив Морской набережной, 45</a>\n"
    "🕕 Начало в 18:00\n\n"
    "Что взять с собой:\n"
    "— ролики;\n"
    "— защиту и шлем (если есть);\n"
    "— воду и удобную одежду.\n\n"
    "Ждём вас на тренировке 🔥"
)


def active_recipients(
    registrations: list[WorkshopRegistration],
    usernames: set[str] | None = None,
) -> list[WorkshopRegistration]:
    normalized_usernames = {value.lstrip("@").lower() for value in usernames or set()}
    recipients: dict[int, WorkshopRegistration] = {}
    for registration in registrations:
        if registration.status != RegistrationStatus.SUBMITTED:
            continue
        username = (registration.telegram_username or "").lstrip("@").lower()
        if normalized_usernames and username not in normalized_usernames:
            continue
        recipients.setdefault(registration.telegram_id, registration)
    return sorted(recipients.values(), key=lambda item: item.telegram_id)


async def run(send: bool, usernames: set[str] | None) -> None:
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
        usernames,
    )

    print(f"Recipients: {len(recipients)}")
    for recipient in recipients:
        print(f"- @{recipient.telegram_username}: {recipient.telegram_id}")
    if not send:
        print("Dry run only. Add --send to deliver the reminder.")
        return
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Reminder image not found: {IMAGE_PATH}")

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
                    link_preview_options=LinkPreviewOptions(is_disabled=True),
                )
                sent += 1
                print(f"Sent to @{recipient.telegram_username}: {recipient.telegram_id}")
            except Exception as exc:
                print(f"Failed for @{recipient.telegram_username}: {recipient.telegram_id}: {exc}")
    finally:
        await bot.session.close()
    print(f"Delivered: {sent}/{len(recipients)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send the Monday workshop reminder.")
    parser.add_argument("--send", action="store_true", help="Actually send messages.")
    parser.add_argument(
        "--all",
        action="store_true",
        help="Send to all active registrations instead of the two test accounts.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    target_usernames = None if args.all else set(DEFAULT_TEST_USERNAMES)
    asyncio.run(run(args.send, target_usernames))
