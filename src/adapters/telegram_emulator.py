"""Telegram Emulator — file/CLI-based message simulation.

Inbound: reads from state/telegram_inbox.jsonl
Outbound: appends to state/telegram_outbox.jsonl

Later replaced by a real Telegram bot adapter.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

from src.runner.time_utils import utc_now

DEFAULT_INBOX_PATH = Path("state/telegram_inbox.jsonl")
DEFAULT_OUTBOX_PATH = Path("state/telegram_outbox.jsonl")


class TelegramEmulator:
    """File-based Telegram message emulator."""

    def __init__(
        self,
        inbox_path: Path | str = DEFAULT_INBOX_PATH,
        outbox_path: Path | str = DEFAULT_OUTBOX_PATH,
    ):
        self.inbox_path = Path(inbox_path)
        self.outbox_path = Path(outbox_path)
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        # Track how many inbox messages have been consumed
        self._inbox_offset = 0

    def enqueue_message(
        self, text: str, chat_id: str = "local-test"
    ) -> dict[str, Any]:
        """Append a user message to the inbox. Returns the message record."""
        record = {
            "ts": utc_now(),
            "type": "user_message",
            "chat_id": chat_id,
            "message_id": str(uuid.uuid4()),
            "text": text,
        }
        with open(self.inbox_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def poll_inbox(self) -> list[dict[str, Any]]:
        """Return new (unconsumed) messages from the inbox and advance the offset."""
        all_messages = self._load_jsonl(self.inbox_path)
        new_messages = all_messages[self._inbox_offset:]
        self._inbox_offset = len(all_messages)
        return new_messages

    def send_message(
        self,
        chat_id: str,
        text: str,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Append an agent message to the outbox. Returns the message record."""
        record = {
            "ts": utc_now(),
            "type": "agent_message",
            "chat_id": chat_id,
            "in_reply_to": in_reply_to or "",
            "text": text,
        }
        with open(self.outbox_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    def get_outbox(self) -> list[dict[str, Any]]:
        """Return all messages from the outbox."""
        return self._load_jsonl(self.outbox_path)

    @staticmethod
    def _load_jsonl(path: Path) -> list[dict[str, Any]]:
        """Load all records from a JSONL file."""
        if not path.exists():
            return []
        records = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
        return records
