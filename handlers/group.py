"""Group handlers: admin-only setup and via_bot message deletion."""
from __future__ import annotations

import logging
import re
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

from storage import (
    BOT_LIST_LIMIT,
    MODE_BLACKLIST,
    MODE_WHITELIST,
    add_bot_to_list,
    ensure_chat,
    get_chat_bot_list,
    get_chat_mode,
    remove_bot_from_list,
    set_chat_mode,
    should_delete_via_bot,
)

router = Router()
log = logging.getLogger(__name__)


def _is_admin(member) -> bool:
    return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))


async def _require_group_admin(message: Message) -> bool:
    if message.chat.type == "private":
        await message.reply("Используйте эту команду в группе, куда меня добавили.")
        return False
    if not message.from_user:
        return False
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        await message.reply("Не удалось проверить права.")
        return False
    if not _is_admin(member):
        await message.reply("Увы, вы не админ.")
        return False
    return True


@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private":
        await message.reply(
            "Добавьте меня в группу, сделайте админом (с правом удалять сообщения), затем там:\n"
            "/ban_bot @имя — удалять сообщения, отправленные через этого бота\n"
            "/allow_bot @имя — не удалять сообщения через этого бота\n"
            "/setmode blacklist | whitelist\n"
            "/list — показать режим и список ботов"
        )
        return
    if not await _require_group_admin(message):
        return
    chat_id = message.chat.id
    await ensure_chat(chat_id)
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    bots = await get_chat_bot_list(chat_id)
    text = (
        f"Режим: {mode}\n"
        f"Ботов: {len(bots)}/{BOT_LIST_LIMIT}\n\n"
        "/ban_bot @имя — добавить бота (чёрный список) или убрать из разрешённых (белый список)\n"
        "/allow_bot @имя — убрать из бана (чёрный список) или добавить в разрешённые (белый список)\n"
        "/setmode blacklist | whitelist\n"
        "/list — показать полный список"
    )
    try:
        await message.reply(text)
        log.info("Sent /start /help in chat %s", chat_id)
    except Exception:
        log.exception("Failed to send /start /help reply in chat %s", chat_id)
        raise


@router.message(Command("ban_bot"), F.text)
async def cmd_ban_bot(message: Message) -> None:
    if not await _require_group_admin(message):
        return
    chat_id = message.chat.id
    text = (message.text or "").strip()
    m = re.match(r"/ban_bot\s+(@?\w+)", text, re.I)
    username = m.group(1) if m else None
    if not username:
        await message.reply("Использование: /ban_bot @имя_бота")
        return
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    if mode == MODE_BLACKLIST:
        ok, msg = await add_bot_to_list(chat_id, username)
    else:
        ok, msg = await remove_bot_from_list(chat_id, username)
    await message.reply(msg)


@router.message(Command("allow_bot"), F.text)
async def cmd_allow_bot(message: Message) -> None:
    if not await _require_group_admin(message):
        return
    chat_id = message.chat.id
    text = (message.text or "").strip()
    m = re.match(r"/allow_bot\s+(@?\w+)", text, re.I)
    username = m.group(1) if m else None
    if not username:
        await message.reply("Использование: /allow_bot @имя_бота")
        return
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    if mode == MODE_BLACKLIST:
        ok, msg = await remove_bot_from_list(chat_id, username)
    else:
        ok, msg = await add_bot_to_list(chat_id, username)
    await message.reply(msg)


@router.message(Command("setmode"), F.text)
async def cmd_setmode(message: Message) -> None:
    if not await _require_group_admin(message):
        return
    chat_id = message.chat.id
    text = (message.text or "").strip().lower()
    m = re.match(r"/setmode\s+(\w+)", text)
    mode = m.group(1) if m else None
    if mode not in (MODE_BLACKLIST, MODE_WHITELIST):
        await message.reply(
            "Использование: /setmode blacklist | whitelist\n"
            "blacklist — удалять только сообщения через перечисленных ботов\n"
            "whitelist — удалять сообщения через любых ботов, кроме перечисленных"
        )
        return
    await set_chat_mode(chat_id, mode)
    await message.reply(f"Режим установлен: {mode}.")


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    if message.chat.type == "private":
        await message.reply("Используйте /list в группе.")
        return
    chat_id = message.chat.id
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    bots = await get_chat_bot_list(chat_id)
    if not bots:
        await message.reply(f"Режим: {mode}. Список ботов пуст.")
        return
    lines = [f"Режим: {mode}", ""] + [f"• @{u}" for u in bots]
    await message.reply("\n".join(lines))


@router.message()
async def on_message(message: Message) -> None:
    if message.chat.type == "private":
        return
    via_bot = message.via_bot
    if not via_bot or not via_bot.username:
        return
    chat_id = message.chat.id
    if not await should_delete_via_bot(chat_id, via_bot.username):
        return
    try:
        await message.delete()
    except Exception:
        pass
