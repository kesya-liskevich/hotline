from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from hotline_bot.config import get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.handlers import build_router
from hotline_bot.storage import RegistrationRepository


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    bot = Bot(settings.bot_token)
    repo = RegistrationRepository(settings.database_path)
    google = GoogleClients(
        settings.google_service_account_file,
        settings.google_sheets_spreadsheet_id,
        settings.google_drive_root_folder_id,
        settings.google_drive_oauth_client_file,
        settings.google_drive_oauth_token_file,
    )
    dispatcher = Dispatcher(storage=MemoryStorage(), events_isolation=SimpleEventIsolation())
    dispatcher.include_router(build_router(repo, google.sheets(), google.drive(), settings))
    await bot.delete_webhook(drop_pending_updates=False)
    await configure_commands(bot, settings.admin_id_set)
    await dispatcher.start_polling(bot)


async def configure_commands(bot: Bot, admin_ids: set[int]) -> None:
    public_commands = [
        BotCommand(command="start", description="открыть меню регистрации"),
        BotCommand(command="registrations", description="мои регистрации"),
    ]
    admin_commands = [
        *public_commands,
        BotCommand(command="id", description="узнать свой Telegram ID"),
        BotCommand(command="stats", description="статистика регистраций"),
        BotCommand(command="export", description="ссылка на таблицу"),
        BotCommand(command="broadcast_competition", description="рассылка участникам"),
    ]
    await bot.set_my_commands(public_commands, scope=BotCommandScopeDefault())
    for admin_id in admin_ids:
        await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))


if __name__ == "__main__":
    asyncio.run(main())
