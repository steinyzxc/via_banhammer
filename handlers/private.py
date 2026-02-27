"""Private chat: redirect to group usage."""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start", "help"))
async def cmd_start_pm(message: Message) -> None:
    if message.chat.type != "private":
        return
    await message.reply(
        "Add me to a group and make me admin (with delete messages). "
        "Then in that group use: /ban\\_bot, /allow\\_bot, /setmode, /list."
    )
