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
        await message.reply("Use this command in a group where I'm added.")
        return False
    if not message.from_user:
        return False
    try:
        member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    except Exception:
        await message.reply("Could not verify permissions.")
        return False
    if not _is_admin(member):
        await message.reply("Only admins can change settings.")
        return False
    return True


@router.message(Command("start", "help"))
async def cmd_start(message: Message) -> None:
    if message.chat.type == "private":
        await message.reply(
            "Add me to a group, make me admin (with delete messages), then use there:\n"
            "/ban_bot @name — delete messages sent via this bot\n"
            "/allow_bot @name — do not delete messages via this bot\n"
            "/setmode blacklist | whitelist\n"
            "/list — show mode and bot list"
        )
        return
    if not await _require_group_admin(message):
        return
    chat_id = message.chat.id
    await ensure_chat(chat_id)
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    bots = await get_chat_bot_list(chat_id)
    text = (
        f"Mode: {mode}\n"
        f"Bots: {len(bots)}/{BOT_LIST_LIMIT}\n\n"
        "/ban_bot @name — add bot (blacklist) or remove from allowed (whitelist)\n"
        "/allow_bot @name — remove from banned (blacklist) or add to allowed (whitelist)\n"
        "/setmode blacklist | whitelist\n"
        "/list — show full list"
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
        await message.reply("Usage: /ban_bot @botusername")
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
        await message.reply("Usage: /allow_bot @botusername")
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
            "Usage: /setmode blacklist | whitelist\n"
            "blacklist = delete only messages via listed bots\n"
            "whitelist = delete messages via any bot not in the list"
        )
        return
    await set_chat_mode(chat_id, mode)
    await message.reply(f"Mode set to {mode}.")


@router.message(Command("list"))
async def cmd_list(message: Message) -> None:
    if message.chat.type == "private":
        await message.reply("Use /list in the group.")
        return
    chat_id = message.chat.id
    mode = await get_chat_mode(chat_id) or MODE_BLACKLIST
    bots = await get_chat_bot_list(chat_id)
    if not bots:
        await message.reply(f"Mode: {mode}. Bot list is empty.")
        return
    lines = [f"Mode: {mode}", ""] + [f"• @{u}" for u in bots]
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
