"""aiogram v3 bot — local polling mode.

Run with: uv run python -m app.bot.main

Full command handlers land in Task #6. This stub proves the token + polling plumbing.
"""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())

    if not settings.telegram_bot_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN missing in .env.local")

    bot = Bot(token=settings.telegram_bot_token)
    dp = Dispatcher()

    @dp.message(Command("start"))
    async def _start(message: Message) -> None:
        await message.answer(
            "TrendRadar 已连上。V1 订阅命令还在路上，先用 /ping 测试连通性。"
        )

    @dp.message(Command("ping"))
    async def _ping(message: Message) -> None:
        await message.answer("pong")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
