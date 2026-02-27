"""Private chat: redirect to group usage."""
from __future__ import annotations

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

router = Router()


@router.message(Command("start", "help"), F.chat.type == "private")
async def cmd_start_pm(message: Message) -> None:
    await message.reply(
        "Добавьте меня в группу и сделайте админом (с правом удалять сообщения). "
        "Затем в той группе используйте: /ban_bot, /allow_bot, /setmode, /list."
    )
