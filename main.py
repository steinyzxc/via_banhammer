"""Entry point for the via-bot filter Telegram bot."""
import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ErrorEvent
from dotenv import load_dotenv

from storage import init_db
from handlers import group, private

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("Set BOT_TOKEN in .env")


async def main() -> None:
    await init_db()
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=None),
    )
    dp = Dispatcher()

    @dp.error()
    async def on_error(event: ErrorEvent) -> None:
        logger.exception(
            "Update %s caused error: %s",
            event.update.model_dump() if event.update else None,
            event.exception,
        )

    dp.include_router(private.router)
    dp.include_router(group.router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
