"""aiogram v3 bot — local polling mode.

Run with: uv run python -m app.bot.main
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.bot.handlers import personal
from app.bot.repo import DbPersonalRepo
from app.config import get_settings
from app.db import AsyncSessionLocal


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env.local")

    bot = Bot(token=settings.telegram_bot_token, default_parse_mode="HTML")
    dp = Dispatcher()

    def _with_repo(handler):
        async def _wrap(msg: Message):
            async with AsyncSessionLocal() as session:
                await handler(msg, repo=DbPersonalRepo(session))
        return _wrap

    dp.message.register(_with_repo(personal.handle_start), Command("start"))
    dp.message.register(_with_repo(personal.handle_subscribe), Command("subscribe"))
    dp.message.register(_with_repo(personal.handle_list), Command("list"))
    dp.message.register(_with_repo(personal.handle_unsubscribe), Command("unsubscribe"))
    dp.message.register(_with_repo(personal.handle_pause), Command("pause"))
    dp.message.register(_with_repo(personal.handle_resume), Command("resume"))

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
