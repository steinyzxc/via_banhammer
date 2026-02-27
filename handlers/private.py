"""Private chat: redirect to group usage."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start", "help"), F.chat.type == "private")
async def cmd_start_pm(message: Message) -> None:
    await message.reply(
        "Add me to a group and make me admin (with delete messages). "
        "Then in that group use: /ban_bot, /allow_bot, /setmode, /list."
    )
