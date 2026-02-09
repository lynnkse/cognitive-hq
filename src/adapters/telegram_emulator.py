"""Telegram Emulator — message adapter.

Inbound: receives from a thread-safe queue (fed by InboxServer or in-process).
Outbound: appends to state/telegram_outbox.jsonl.

Later replaced by a real Telegram bot adapter.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from queue import Empty, Queue
from typing import Any

from src.runner.time_utils import utc_now

DEFAULT_OUTBOX_PATH = Path("state/telegram_outbox.jsonl")


class TelegramEmulator:
    """Queue-based inbound, file-based outbound Telegram adapter."""

    def __init__(
        self,
        outbox_path: Path | str = DEFAULT_OUTBOX_PATH,
        inbox_queue: Queue | None = None,
    ):
        self.outbox_path = Path(outbox_path)
        self.outbox_path.parent.mkdir(parents=True, exist_ok=True)
        self._inbox_queue = inbox_queue or Queue()

    @property
    def inbox_queue(self) -> Queue:
        """Expose the queue so InboxServer can be wired to it."""
        return self._inbox_queue

    def enqueue_message(
        self, text: str, chat_id: str = "local-test"
    ) -> dict[str, Any]:
        """Put a message directly into the inbox queue (in-process path).

        Used by tests and for in-process message injection.
        For cross-process delivery, use InboxClient -> InboxServer instead.
        """
        record = {
            "ts": utc_now(),
            "type": "user_message",
            "chat_id": chat_id,
            "message_id": str(uuid.uuid4()),
            "text": text,
        }
        self._inbox_queue.put(record)
        return record

    def poll_inbox(self) -> list[dict[str, Any]]:
        """Drain all available messages from the inbox queue.

        Non-blocking: returns whatever is in the queue right now.
        """
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
