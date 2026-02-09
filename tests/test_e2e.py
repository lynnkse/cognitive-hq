"""End-to-end integration tests for the full agent loop.

MVP-7 success criteria:
  [x] Start the runner
  [x] Send a message via CLI
  [x] Get a reply via CloudCode
  [x] Memory put/search/get_latest work
  [x] Transcript logged
  [x] Agent survives CloudCode failure gracefully

These tests mock only the CloudCode CLI subprocess call.
Everything else (adapters, registry, runner, state, transcripts) runs for real.
"""

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.runner.agent_runner import AgentRunner
from src.runner.cloudcode_bridge import CloudCodeBridge, CloudCodeError
from src.runner.plan_schema import ExecutionPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fake_plan_reply(text: str, chat_id: str = "local-test") -> str:
    """Return raw JSON string that CloudCode would produce for a simple reply."""
    return json.dumps({
        "assistant_message": f"Replying to: {text}",
        "tool_calls": [
            {"tool_name": "telegram_send_message",
             "args": {"chat_id": chat_id, "text": f"Echo: {text}"}},
        ],
        "state_patch": {},
        "notes": "",
    })


def fake_plan_memory_put(text: str, chat_id: str = "local-test") -> str:
    """Return raw JSON for a plan that stores a memory and replies."""
    return json.dumps({
        "assistant_message": "Storing user preference.",
        "tool_calls": [
            {"tool_name": "memory_put",
             "args": {"text": text, "tags": ["preference"], "source": "conversation", "metadata": {}}},
            {"tool_name": "telegram_send_message",
             "args": {"chat_id": chat_id, "text": f"Stored: {text}"}},
        ],
        "state_patch": {"last_action": "memory_put"},
        "notes": "User asked to remember something.",
    })


def fake_plan_memory_search(query: str, chat_id: str = "local-test") -> str:
    """Return raw JSON for a plan that searches memory."""
    return json.dumps({
        "assistant_message": "Searching memory.",
        "tool_calls": [
            {"tool_name": "memory_search",
             "args": {"query": query, "k": 5}},
        ],
        "state_patch": {},
        "notes": "",
    })


def fake_plan_memory_latest(chat_id: str = "local-test") -> str:
    """Return raw JSON for a plan that gets latest memories."""
    return json.dumps({
        "assistant_message": "Getting latest memories.",
        "tool_calls": [
            {"tool_name": "memory_get_latest", "args": {"n": 10}},
        ],
        "state_patch": {},
        "notes": "",
    })


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def env(tmp_path):
    """Wire up the full stack with real adapters and a real bridge (CLI mocked)."""
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir()
    for name in ["system_context.md", "tool_contract.md", "output_format.md", "examples.md"]:
        (prompts_dir / name).write_text(f"# {name}")

    tg = TelegramEmulator(
        outbox_path=tmp_path / "outbox.jsonl",
    )
    mem = MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")
    bridge = CloudCodeBridge(prompts_dir=prompts_dir)

    runner = AgentRunner(
        telegram=tg,
        memory=mem,
        bridge=bridge,
        state_path=tmp_path / "agent_state.json",
        conversations_dir=tmp_path / "conversations",
    )
    return {
        "runner": runner,
        "tg": tg,
        "mem": mem,
        "bridge": bridge,
        "tmp_path": tmp_path,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestE2E_SendAndReply:
    """Start the runner, send a message, get a reply."""

    def test_send_message_get_reply(self, env):
        """Full cycle: enqueue message → runner processes → reply in outbox."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        # Mock the CLI call to return a simple reply plan
        with patch.object(bridge, "_call_cli", return_value=fake_plan_reply("hello")):
            tg.enqueue_message("hello")
            results = runner.run_once()

        # Should have one successful tool result (telegram_send_message)
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["tool_name"] == "telegram_send_message"

        # Outbox should have the reply
        outbox = tg.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["text"] == "Echo: hello"
        assert outbox[0]["type"] == "agent_message"

    def test_multiple_messages_in_sequence(self, env):
        """Multiple messages processed in order."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "_call_cli", side_effect=[
            fake_plan_reply("msg1"),
            fake_plan_reply("msg2"),
        ]):
            tg.enqueue_message("msg1")
            tg.enqueue_message("msg2")
            results = runner.run_once()

        assert len(results) == 2
        outbox = tg.get_outbox()
        assert len(outbox) == 2
        assert outbox[0]["text"] == "Echo: msg1"
        assert outbox[1]["text"] == "Echo: msg2"


class TestE2E_Memory:
    """Memory put / search / get_latest work end-to-end."""

    def test_memory_put_and_retrieve(self, env):
        """Store a memory via plan, then verify it exists."""
        tg, runner, bridge, mem = env["tg"], env["runner"], env["bridge"], env["mem"]

        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_memory_put("User prefers Python")):
            tg.enqueue_message("remember I prefer Python")
            runner.run_once()

        # Memory should contain the entry
        latest = mem.memory_get_latest(1)
        assert len(latest) == 1
        assert latest[0]["text"] == "User prefers Python"
        assert latest[0]["tags"] == ["preference"]

        # Outbox should have the confirmation
        outbox = tg.get_outbox()
        assert "Stored" in outbox[0]["text"]

    def test_memory_search_via_plan(self, env):
        """Pre-populate memory, then search via a plan."""
        tg, runner, bridge, mem = env["tg"], env["runner"], env["bridge"], env["mem"]

        # Pre-populate memory directly
        mem.memory_put("User prefers Python", tags=["preference"])
        mem.memory_put("User lives in Tel Aviv", tags=["location"])

        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_memory_search("Python")):
            tg.enqueue_message("what do you know about Python?")
            results = runner.run_once()

        # memory_search should return matching results
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["tool_name"] == "memory_search"
        search_results = results[0]["result"]
        assert len(search_results) == 1
        assert "Python" in search_results[0]["text"]

    def test_memory_get_latest_via_plan(self, env):
        """Pre-populate memory, then get latest via a plan."""
        tg, runner, bridge, mem = env["tg"], env["runner"], env["bridge"], env["mem"]

        mem.memory_put("first note")
        mem.memory_put("second note")
        mem.memory_put("third note")

        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_memory_latest()):
            tg.enqueue_message("show me recent memories")
            results = runner.run_once()

        assert results[0]["success"] is True
        latest = results[0]["result"]
        assert len(latest) == 3
        assert latest[0]["text"] == "third note"  # newest first


class TestE2E_Transcript:
    """Transcript is logged to session file."""

    def test_transcript_contains_full_cycle(self, env):
        """Session file records user message, assistant plan, and tool results."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "_call_cli", return_value=fake_plan_reply("hello")):
            tg.enqueue_message("hello")
            runner.run_once()

        session_file = runner._session_path
        assert session_file.exists()

        lines = session_file.read_text().strip().split("\n")
        entries = [json.loads(line) for line in lines]

        roles = [e["role"] for e in entries]
        assert "user" in roles
        assert "assistant" in roles
        assert "tool_results" in roles

        # User entry should contain the message text
        user_entry = next(e for e in entries if e["role"] == "user")
        assert user_entry["content"]["text"] == "hello"

        # Assistant entry should contain the plan
        assistant_entry = next(e for e in entries if e["role"] == "assistant")
        assert "tool_calls" in assistant_entry["content"]

    def test_transcript_accumulates_across_messages(self, env):
        """Multiple messages each add to the same session transcript."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "_call_cli", side_effect=[
            fake_plan_reply("first"),
            fake_plan_reply("second"),
        ]):
            tg.enqueue_message("first")
            runner.run_once()
            tg.enqueue_message("second")
            runner.run_once()

        lines = runner._session_path.read_text().strip().split("\n")
        # Each message produces 3 entries (user, assistant, tool_results) = 6 total
        assert len(lines) == 6


class TestE2E_StatePersistence:
    """Agent state persists across ticks and survives restart."""

    def test_state_patch_persisted(self, env):
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_memory_put("note")):
            tg.enqueue_message("remember something")
            runner.run_once()

        # State should have been patched and saved
        state = json.loads(env["tmp_path"].joinpath("agent_state.json").read_text())
        assert state["last_action"] == "memory_put"

    def test_state_survives_new_runner_instance(self, env):
        """A new runner instance loads state from disk."""
        tg, runner, bridge, mem = env["tg"], env["runner"], env["bridge"], env["mem"]

        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_memory_put("note")):
            tg.enqueue_message("remember something")
            runner.run_once()

        # Create a brand new runner instance (simulates restart)
        runner2 = AgentRunner(
            telegram=tg,
            memory=mem,
            bridge=bridge,
            state_path=env["tmp_path"] / "agent_state.json",
            conversations_dir=env["tmp_path"] / "conversations",
        )
        assert runner2._agent_state["last_action"] == "memory_put"


class TestE2E_CloudCodeFailure:
    """Agent survives CloudCode failures gracefully."""

    def test_survives_cloudcode_error(self, env):
        """CloudCode error doesn't crash the runner, returns empty results."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "invoke",
                          side_effect=CloudCodeError("connection refused")):
            tg.enqueue_message("hello")
            results = runner.run_once()

        # Should not crash, returns empty results
        assert results == []

    def test_recovers_after_cloudcode_failure(self, env):
        """After a CloudCode failure, the next message processes normally."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        # First message: CloudCode fails
        with patch.object(bridge, "invoke",
                          side_effect=CloudCodeError("timeout")):
            tg.enqueue_message("this will fail")
            runner.run_once()

        # Second message: CloudCode works
        with patch.object(bridge, "_call_cli",
                          return_value=fake_plan_reply("retry")):
            tg.enqueue_message("this should work")
            results = runner.run_once()

        assert len(results) == 1
        assert results[0]["success"] is True
        outbox = tg.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["text"] == "Echo: retry"

    def test_failure_logged_in_transcript(self, env):
        """CloudCode failure is recorded in the session transcript."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "invoke",
                          side_effect=CloudCodeError("API error")):
            tg.enqueue_message("hello")
            runner.run_once()

        lines = runner._session_path.read_text().strip().split("\n")
        entries = [json.loads(line) for line in lines]
        # Should have user entry + system error entry
        roles = [e["role"] for e in entries]
        assert "user" in roles
        assert "system" in roles
        error_entry = next(e for e in entries if e["role"] == "system")
        assert "error" in error_entry["content"]


class TestE2E_RunLoop:
    """Test the actual run() loop with threading."""

    def test_run_and_stop(self, env):
        """Runner can be started and stopped cleanly via threading."""
        tg, runner, bridge = env["tg"], env["runner"], env["bridge"]

        with patch.object(bridge, "_call_cli", return_value=fake_plan_reply("bg")):
            # Enqueue a message before starting
            tg.enqueue_message("background test")

            # Run in a thread with short poll interval
            runner.poll_interval = 0.1
            thread = threading.Thread(target=runner.run, daemon=True)
            thread.start()

            # Wait for it to process
            time.sleep(0.5)
            runner.stop()
            thread.join(timeout=2.0)

        assert not thread.is_alive()
        outbox = tg.get_outbox()
        assert len(outbox) >= 1
        assert outbox[0]["text"] == "Echo: bg"
