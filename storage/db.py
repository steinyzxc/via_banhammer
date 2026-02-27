"""SQLite storage for chat configs and bot lists."""
from __future__ import annotations

import aiosqlite
from pathlib import Path

BOT_LIST_LIMIT = 100
MODE_BLACKLIST = "blacklist"
MODE_WHITELIST = "whitelist"

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "bot_filter.db"


async def init_db() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS chat_settings (
                chat_id INTEGER PRIMARY KEY,
                mode TEXT NOT NULL DEFAULT 'blacklist' CHECK (mode IN ('blacklist', 'whitelist'))
            )
            """
        )
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_list (
                chat_id INTEGER NOT NULL,
                bot_username TEXT NOT NULL,
                PRIMARY KEY (chat_id, bot_username),
                FOREIGN KEY (chat_id) REFERENCES chat_settings(chat_id)
            )
            """
        )
        await db.commit()


def _norm_username(username: str | None) -> str | None:
    if not username:
        return None
    s = username.strip().lstrip("@").lower()
    return s if s else None


async def get_chat_mode(chat_id: int) -> str | None:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT mode FROM chat_settings WHERE chat_id = ?", (chat_id,)
        )
        row = await cur.fetchone()
        return row["mode"] if row else None


async def get_chat_bot_list(chat_id: int) -> list[str]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT bot_username FROM bot_list WHERE chat_id = ? ORDER BY bot_username",
            (chat_id,),
        )
        rows = await cur.fetchall()
        return [r[0] for r in rows]


async def ensure_chat(chat_id: int, mode: str = MODE_BLACKLIST) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO chat_settings (chat_id, mode) VALUES (?, ?)",
            (chat_id, mode),
        )
        await db.commit()


async def set_chat_mode(chat_id: int, mode: str) -> None:
    await ensure_chat(chat_id, mode)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE chat_settings SET mode = ? WHERE chat_id = ?", (mode, chat_id)
        )
        await db.commit()


async def add_bot_to_list(chat_id: int, username: str) -> tuple[bool, str]:
    username = _norm_username(username)
    if not username:
        return False, "Некорректное имя пользователя."
    await ensure_chat(chat_id)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM bot_list WHERE chat_id = ?", (chat_id,)
        )
        (count,) = (await cur.fetchone()) or (0,)
        if count >= BOT_LIST_LIMIT:
            return False, f"Достигнут лимит списка ботов ({BOT_LIST_LIMIT})."
        await db.execute(
            "INSERT OR IGNORE INTO bot_list (chat_id, bot_username) VALUES (?, ?)",
            (chat_id, username),
        )
        await db.commit()
    return True, f"Добавлен @{username}."


async def remove_bot_from_list(chat_id: int, username: str) -> tuple[bool, str]:
    username = _norm_username(username)
    if not username:
        return False, "Некорректное имя пользователя."
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "DELETE FROM bot_list WHERE chat_id = ? AND bot_username = ?",
            (chat_id, username),
        )
        await db.commit()
        if cur.rowcount:
            return True, f"Удалён @{username}."
    return False, f"@{username} не был в списке."


async def should_delete_via_bot(chat_id: int, via_bot_username: str | None) -> bool:
    if not via_bot_username:
        return False
    username = _norm_username(via_bot_username)
    if not username:
        return False
    mode = await get_chat_mode(chat_id)
    if mode is None:
        return False
    bots = await get_chat_bot_list(chat_id)
    if mode == MODE_BLACKLIST:
        return username in bots
    else:
        return username not in bots
