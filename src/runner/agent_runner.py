"""Agent Runner — always-on loop that orchestrates the agent.

Receives inbound messages, invokes CloudCode for decisions,
executes tool calls, and persists state.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.adapters.inbox_server import InboxServer
from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.adapters.tool_registry import ToolRegistry
from src.runner.cloudcode_bridge import CloudCodeBridge, CloudCodeError
from src.runner.logging_utils import append_to_transcript
from src.runner.plan_schema import ExecutionPlan

logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path("state/agent_state.json")
DEFAULT_CONVERSATIONS_DIR = Path("state/conversations")


class AgentRunner:
    """Always-on loop that polls for messages and orchestrates responses."""

    def __init__(
        self,
        telegram: TelegramEmulator,
        memory: MemoryEmulator,
        bridge: CloudCodeBridge,
        state_path: Path | str = DEFAULT_STATE_PATH,
        conversations_dir: Path | str = DEFAULT_CONVERSATIONS_DIR,
        poll_interval: float = 2.0,
        max_transcript_messages: int = 20,
        socket_path: Path | str | None = None,
    ):
        self.telegram = telegram
        self.memory = memory
        self.bridge = bridge
        self.registry = ToolRegistry(telegram=telegram, memory=memory)
        self.state_path = Path(state_path)
        self.conversations_dir = Path(conversations_dir)
        self.poll_interval = poll_interval
        self.max_transcript_messages = max_transcript_messages

        self._running = False
        self._agent_state = self._load_state()
        self._transcript: list[dict[str, Any]] = []
        self._session_path = self._make_session_path()

        # Socket server for cross-process message delivery (None in tests)
        self._inbox_server: InboxServer | None = None
        if socket_path is not None:
            self._inbox_server = InboxServer(
                queue=telegram.inbox_queue,
                socket_path=socket_path,
            )

    def run(self) -> None:
        """Start the polling loop. Blocks until stop() is called or interrupted."""
        self._running = True
        if self._inbox_server:
            self._inbox_server.start()
        logger.info("Agent runner started (poll_interval=%.1fs)", self.poll_interval)
        try:
            while self._running:
                self._tick()
                if self._running:
                    time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Agent runner interrupted by user")
        finally:
            self._running = False
            if self._inbox_server:
                self._inbox_server.stop()
            logger.info("Agent runner stopped")

    def stop(self) -> None:
        """Signal the runner to stop after the current tick."""
        self._running = False

    def run_once(self) -> list[dict[str, Any]]:
        """Process all pending messages in a single pass. Returns tool results.

        Useful for testing and scripted usage.
        """
        return self._tick()

    def _tick(self) -> list[dict[str, Any]]:
        """Poll for new messages and process each one. Returns all tool results."""
        all_results: list[dict[str, Any]] = []
        messages = self.telegram.poll_inbox()
        for msg in messages:
            results = self._handle_message(msg)
            all_results.extend(results)
        return all_results

    def _handle_message(self, msg: dict[str, Any]) -> list[dict[str, Any]]:
        """Process a single inbound message through the full cycle."""
        user_text = msg.get("text", "")
        chat_id = msg.get("chat_id", "local-test")
        message_id = msg.get("message_id", "")

        logger.info("Processing message [%s]: %s", message_id[:8], user_text[:80])

        # Log to transcript
        self._append_transcript("user", msg)

        # Invoke CloudCode
        try:
            plan = self.bridge.invoke(
                user_message=user_text,
                chat_id=chat_id,
                transcript=self._recent_transcript(),
                agent_state=self._agent_state,
            )
        except CloudCodeError as e:
            logger.error("CloudCode failed: %s", e)
            self._append_transcript("system", {"error": str(e)})
            return []

        # Log the plan
        self._append_transcript("assistant", plan.model_dump())

        # Execute tool calls
        results = self.registry.execute_all(plan.tool_calls)
        if results:
            self._append_transcript("tool_results", results)

        # Apply state patch
        if plan.state_patch:
            self._agent_state.update(plan.state_patch)
            self._save_state()

        # Log notes
        if plan.notes:
            logger.info("CloudCode notes: %s", plan.notes)

        return results

    def _recent_transcript(self) -> list[dict[str, Any]]:
        """Return the last N transcript entries for context."""
        return self._transcript[-self.max_transcript_messages:]

    def _append_transcript(self, role: str, content: Any) -> None:
        """Append to in-memory transcript and persist to session file."""
        self._transcript.append({"role": role, "content": content})
        append_to_transcript(self._session_path, role, content)

    def _load_state(self) -> dict[str, Any]:
        """Load agent state from disk, or return empty dict."""
        if self.state_path.exists():
            text = self.state_path.read_text().strip()
            if text:
                return json.loads(text)
        return {}

    def _save_state(self) -> None:
        """Persist agent state to disk."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_path, "w") as f:
            json.dump(self._agent_state, f, indent=2)

    def _make_session_path(self) -> Path:
        """Generate a session transcript path based on current date."""
        date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        self.conversations_dir.mkdir(parents=True, exist_ok=True)
        return self.conversations_dir / f"session_{date_str}.jsonl"
