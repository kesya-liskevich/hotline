from __future__ import annotations

import asyncio
import logging
import os

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage, SimpleEventIsolation
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from hotline_bot.config import Settings, get_settings
from hotline_bot.google_services import GoogleClients
from hotline_bot.handlers import build_router
from hotline_bot.storage import RegistrationRepository


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    logging.info("Starting Hotline bot process pid=%s", os.getpid())
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
    await configure_commands(bot, settings.admin_id_set)
    webhook_url = _webhook_url(settings)
    if webhook_url:
        await start_webhook(bot, dispatcher, settings, webhook_url)
        return
    await start_polling(bot, dispatcher)


async def start_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    logging.info("Starting polling mode")
    await bot.delete_webhook(drop_pending_updates=False)
    await dispatcher.start_polling(bot)


async def start_webhook(
    bot: Bot,
    dispatcher: Dispatcher,
    settings: Settings,
    webhook_url: str,
) -> None:
    webhook_path = _webhook_path(settings)
    logging.info("Starting webhook mode on port %s path %s", settings.port, webhook_path)
    await bot.set_webhook(webhook_url, drop_pending_updates=False)

    app = web.Application()
    app.router.add_get("/", _healthcheck)
    SimpleRequestHandler(dispatcher=dispatcher, bot=bot).register(app, path=webhook_path)
    setup_application(app, dispatcher, bot=bot)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=settings.port)
    await site.start()
    logging.info("Webhook is ready: %s", webhook_url)
    await asyncio.Event().wait()


async def _healthcheck(request: web.Request) -> web.Response:
    return web.Response(text="ok")


def _webhook_url(settings: Settings) -> str | None:
    base_url = settings.webhook_url or settings.render_external_url
    if not base_url:
        return None
    if base_url.endswith(_webhook_path(settings)):
        return base_url
    return f"{base_url.rstrip('/')}{_webhook_path(settings)}"


def _webhook_path(settings: Settings) -> str:
    bot_id = settings.bot_token.split(":", 1)[0]
    return f"/telegram/webhook/{bot_id}"


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
