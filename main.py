"""Entry point for the via-bot filter Telegram bot."""
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from storage import init_db
from handlers import group, private

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in .env")


async def main() -> None:
    await init_db()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher()
    dp.include_router(private.router)
    dp.include_router(group.router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
