# Via-Bot Filter Telegram Bot

Deletes messages in a group that were sent **via** specific inline bots (e.g. "via @dickgrowerbot"). All setup is done **in the chat** by admins. Blacklist/whitelist modes; bot list size limited.

## Requirements

- Python 3.10+
- Bot must be **group admin** with **delete messages** permission.

## Setup

1. Create a bot with [@BotFather](https://t.me/BotFather), copy the token.
2. `cp .env.example .env` and set `BOT_TOKEN`.
3. `pip install -r requirements.txt`
4. Run: `python main.py`

## Docker

```bash
cp .env.example .env   # задать BOT_TOKEN
docker compose up -d
```

Образ на `python:3.12-slim`, данные в volume `bot_data`. Без systemd.

## Deploy with GitHub Actions

Workflow: `.github/workflows/deploy.yml`. Runs only when triggered manually: **Actions → Deploy → Run workflow**.

**Full step-by-step for a new VM:** [docs/DEPLOY-VM.md](docs/DEPLOY-VM.md)

**Secrets** (Settings → Secrets and variables → Actions):

| Secret | Required | Description |
|--------|----------|-------------|
| `BOT_TOKEN` | Yes | Telegram bot token from @BotFather |
| `SSH_HOST` | Yes | Server hostname or IP |
| `SSH_USER` | Yes | SSH login user |
| `SSH_PRIVATE_KEY` | Yes | Private key (e.g. contents of `id_ed25519`) for deploy |

**One-time on server**

1. Install Docker and Docker Compose.
2. Create app dir and allow `SSH_USER` to write:  
   `sudo mkdir -p /opt/telegram-bot-filter && sudo chown $USER /opt/telegram-bot-filter`

Deploy: workflow copies archive to server, extracts into deploy path, writes `.env` from `BOT_TOKEN`, runs `docker compose up -d --build`. Data (DB) in Docker volume `bot_data`. No systemd.

## Usage (in the group)

Admins only. All commands are used in the group you want to protect.

- **/ban_bot** @botusername — In blacklist: add bot (its messages will be deleted). In whitelist: remove from allowed list.
- **/allow_bot** @botusername — In blacklist: remove bot from list (stop deleting it). In whitelist: add bot to allowed list.
- **/setmode** blacklist | whitelist — blacklist = delete only messages via listed bots; whitelist = delete messages via any bot not in the list.
- **/list** — show current mode and full bot list.
- **/start** or **/help** — short help and current state.

In private chat, **/start** shows the same instructions.

## Limits

- Bot list: **100** entries per chat (`BOT_LIST_LIMIT` in `storage/db.py`).

## Behaviour

- Only messages with **via @bot** attribution are considered. Normal user/bot messages are left alone.
- **Blacklist**: delete if `message.via_bot` username is in the list.
- **Whitelist**: delete if `message.via_bot` is set and username is **not** in the list (empty list = delete all via-bot messages).

## Data

- SQLite: `data/bot_filter.db` (created on first run).
