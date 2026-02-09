# How to Swap the Telegram Emulator for a Real Telegram Bot

You already have a bot (created via @BotFather). This guide explains exactly what to change to connect it to the agent.

---

## How the System Works Now

```
send_message.py  --Unix socket-->  InboxServer  -->  Queue  -->  AgentRunner
                                                                      |
                                                                      v
                                                             CloudCode (claude CLI)
                                                                      |
                                                                      v
                                                             TelegramEmulator.send_message()
                                                                      |
                                                                      v
                                                             state/telegram_outbox.jsonl (file)
```

The emulator does two things:
1. **Inbound**: Messages come in via Unix socket (from `send_message.py`) and get queued
2. **Outbound**: Agent replies go to `state/telegram_outbox.jsonl` (a file nobody reads)

With a real Telegram bot:
1. **Inbound**: Messages come from Telegram's servers via webhook or long-polling
2. **Outbound**: Agent replies get sent to Telegram via the Bot API

---

## What Needs to Change

### Overview

You need to create one new file: `src/adapters/telegram_bot.py`. This replaces the emulator with a real Telegram adapter that has the same interface.

Nothing else in the system needs to change — the agent runner, CloudCode bridge, tool registry, memory, and plan schema are all untouched.

```
BEFORE:                              AFTER:
TelegramEmulator                     TelegramBot
  .poll_inbox()  (drain queue)         .poll_inbox()  (Telegram long-poll)
  .send_message() (write file)         .send_message() (Bot API HTTP call)
  .enqueue_message() (test only)       .enqueue_message() (not needed)
```

### The Interface Contract

The agent runner calls exactly two methods on the Telegram adapter:

```python
# Called every tick to get new messages
messages: list[dict] = telegram.poll_inbox()
# Each message dict must have: {"text": str, "chat_id": str, "message_id": str, "ts": str, "type": "user_message"}

# Called by the tool registry when CloudCode returns a telegram_send_message tool call
result: dict = telegram.send_message(chat_id=str, text=str, in_reply_to=str|None)
```

As long as your new adapter implements these two methods with the same signatures and return formats, everything works.

---

## Step-by-Step Implementation

### Step 1: Install python-telegram-bot

```bash
pip install python-telegram-bot
```

This is the most popular Python Telegram library. It wraps the Telegram Bot API.

### Step 2: Create `src/adapters/telegram_bot.py`

```python
"""Real Telegram bot adapter.

Drop-in replacement for TelegramEmulator.
Same interface: poll_inbox() and send_message().
"""

from __future__ import annotations

import logging
import uuid
from queue import Empty, Queue
from typing import Any

from telegram import Bot, Update
from telegram.ext import Application, MessageHandler, filters

from src.runner.time_utils import utc_now

logger = logging.getLogger(__name__)


class TelegramBot:
    """Real Telegram bot adapter using long-polling."""

    def __init__(self, token: str, allowed_chat_ids: list[str] | None = None):
        """
        Args:
            token: Bot token from @BotFather
            allowed_chat_ids: If set, only accept messages from these chat IDs.
                              Use this to restrict the bot to your account only.
        """
        self._token = token
        self._allowed_chat_ids = set(str(cid) for cid in allowed_chat_ids) if allowed_chat_ids else None
        self._inbox_queue: Queue = Queue()
        self._bot = Bot(token=token)
        self._app: Application | None = None

    @property
    def inbox_queue(self) -> Queue:
        return self._inbox_queue

    def start(self) -> None:
        """Start the Telegram long-polling in a background thread.

        Call this before the agent runner starts polling.
        """
        self._app = (
            Application.builder()
            .token(self._token)
            .build()
        )
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        # Run polling in a separate thread so it doesn't block the agent runner
        import threading
        self._poll_thread = threading.Thread(target=self._run_polling, daemon=True)
        self._poll_thread.start()
        logger.info("Telegram bot started (long-polling)")

    def _run_polling(self) -> None:
        """Run the telegram polling loop (blocking, runs in thread)."""
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._app.initialize())
        loop.run_until_complete(self._app.start())
        loop.run_until_complete(self._app.updater.start_polling())
        loop.run_forever()

    async def _on_message(self, update: Update, context) -> None:
        """Handle an incoming Telegram message."""
        msg = update.message
        if msg is None or msg.text is None:
            return

        chat_id = str(msg.chat_id)

        # Security: reject messages from unauthorized chats
        if self._allowed_chat_ids and chat_id not in self._allowed_chat_ids:
            logger.warning("Rejected message from unauthorized chat_id: %s", chat_id)
            return

        record = {
            "ts": utc_now(),
            "type": "user_message",
            "chat_id": chat_id,
            "message_id": str(msg.message_id),
            "text": msg.text,
        }
        self._inbox_queue.put(record)
        logger.info("Received Telegram message from chat %s: %s", chat_id, msg.text[:80])

    def poll_inbox(self) -> list[dict[str, Any]]:
        """Drain all available messages from the inbox queue."""
        messages = []
        while True:
            try:
                messages.append(self._inbox_queue.get_nowait())
            except Empty:
                break
        return messages

    def send_message(
        self,
        chat_id: str,
        text: str,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Send a message to a Telegram chat via the Bot API."""
        import asyncio

        async def _send():
            return await self._bot.send_message(
                chat_id=int(chat_id),
                text=text,
                reply_to_message_id=int(in_reply_to) if in_reply_to else None,
            )

        # Run the async send in a new event loop (we're in a sync context)
        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(_send())
        finally:
            loop.close()

        record = {
            "ts": utc_now(),
            "type": "agent_message",
            "chat_id": chat_id,
            "in_reply_to": in_reply_to or "",
            "text": text,
            "telegram_message_id": result.message_id,
        }
        logger.info("Sent Telegram message to chat %s: %s", chat_id, text[:80])
        return record

    def stop(self) -> None:
        """Stop the Telegram polling."""
        if self._app:
            import asyncio
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(self._app.updater.stop())
                loop.run_until_complete(self._app.stop())
                loop.run_until_complete(self._app.shutdown())
            finally:
                loop.close()
        logger.info("Telegram bot stopped")

    def enqueue_message(self, text: str, chat_id: str = "local-test") -> dict[str, Any]:
        """For testing only. Injects a message directly into the queue."""
        record = {
            "ts": utc_now(),
            "type": "user_message",
            "chat_id": chat_id,
            "message_id": str(uuid.uuid4()),
            "text": text,
        }
        self._inbox_queue.put(record)
        return record
```

This is a starting point. You'll likely want to refine the async handling — `python-telegram-bot` v20+ is fully async, so the exact integration depends on how you want to handle the event loop. The pattern above (background thread with its own event loop) works but isn't the prettiest.

**Alternative: use `python-telegram-bot` v13 (sync API)** — simpler but older:
```bash
pip install python-telegram-bot==13.15
```
With v13, you don't need async/await at all — everything is sync.

### Step 3: Update `src/cli/run_agent.py`

Change the adapter initialization based on config:

```python
from pathlib import Path
import yaml

# Load config
config_path = Path("config/settings.local.yaml")
if config_path.exists():
    with open(config_path) as f:
        config = yaml.safe_load(f)
else:
    config = {}

telegram_mode = config.get("telegram", {}).get("mode", "emulator")

if telegram_mode == "live":
    from src.adapters.telegram_bot import TelegramBot
    token = config["telegram"]["bot_token"]
    allowed = config["telegram"].get("allowed_chat_ids")
    telegram = TelegramBot(token=token, allowed_chat_ids=allowed)
    telegram.start()
    socket_path = None  # No socket server needed — Telegram provides inbound
else:
    from src.adapters.telegram_emulator import TelegramEmulator
    telegram = TelegramEmulator()
    socket_path = Path("state/agent.sock")

runner = AgentRunner(
    telegram=telegram,
    memory=memory,
    bridge=bridge,
    poll_interval=args.poll_interval,
    socket_path=socket_path,
)
```

### Step 4: Update `config/settings.local.yaml`

```yaml
agent:
  poll_interval_seconds: 2
  socket_path: state/agent.sock

cloudcode:
  model: haiku
  timeout_seconds: 30

telegram:
  mode: live                           # <-- change from "emulator" to "live"
  bot_token: "123456:ABC-DEF..."       # <-- your token from @BotFather
  allowed_chat_ids:                    # <-- restrict to your account
    - "your_telegram_user_id"          # Find this by messaging @userinfobot

memory:
  mode: emulator
  search_results_k: 5

logging:
  level: INFO
```

### Step 5: Find your Telegram chat ID

You need your numeric chat ID to restrict the bot to your account only:

1. Message your bot on Telegram (say "hi")
2. Open this URL in your browser: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
3. Find the `"chat": {"id": 123456789}` in the response — that's your chat ID
4. Put it in `allowed_chat_ids` in the config

### Step 6: Test

```bash
# Start the agent in live mode
python3 src/cli/run_agent.py

# Open Telegram on your phone/desktop
# Send a message to your bot
# You should see the agent process it and reply
```

---

## What Changes, What Doesn't

| Component | Changes? | Why |
|-----------|----------|-----|
| `telegram_emulator.py` | No | Still exists for local testing |
| `telegram_bot.py` | New | Real Telegram adapter |
| `run_agent.py` | Yes | Config-based adapter selection |
| `settings.local.yaml` | Yes | Add token and mode |
| `agent_runner.py` | No | Calls same interface (`poll_inbox`, `send_message`) |
| `cloudcode_bridge.py` | No | Doesn't know about Telegram |
| `tool_registry.py` | No | Dispatches to whichever adapter is passed in |
| `memory_emulator.py` | No | Independent of Telegram |
| `plan_schema.py` | No | Independent of Telegram |
| `send_message.py` CLI | Not needed | You'll use Telegram directly |
| `inbox_server.py` | Not needed | Telegram replaces the socket server for inbound |

---

## Security Notes

- **Never commit your bot token.** `settings.local.yaml` is gitignored.
- **Always set `allowed_chat_ids`** to restrict the bot to your account. Without this, anyone who finds your bot can talk to it (and it will invoke CloudCode on their behalf, costing you money).
- **The bot token gives full control** of the bot. Treat it like a password.

---

## Rollback

To go back to the emulator, just change `telegram.mode` back to `"emulator"` in your config:

```yaml
telegram:
  mode: emulator
```

No code changes needed. The emulator and socket server kick in automatically.
