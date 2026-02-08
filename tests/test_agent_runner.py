"""Tests for the agent runner."""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.runner.agent_runner import AgentRunner
from src.runner.cloudcode_bridge import CloudCodeBridge, CloudCodeError
from src.runner.plan_schema import ExecutionPlan, ToolCall, ToolName


def make_plan(
    message: str = "",
    tool_calls: list | None = None,
    state_patch: dict | None = None,
    notes: str = "",
) -> ExecutionPlan:
    """Helper to build an ExecutionPlan."""
    return ExecutionPlan(
        assistant_message=message,
        tool_calls=tool_calls or [],
        state_patch=state_patch or {},
        notes=notes,
    )


@pytest.fixture
def env(tmp_path):
    """Set up a full agent environment with a mock bridge."""
    tg = TelegramEmulator(
        inbox_path=tmp_path / "inbox.jsonl",
        outbox_path=tmp_path / "outbox.jsonl",
    )
    mem = MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")
    bridge = MagicMock(spec=CloudCodeBridge)
    runner = AgentRunner(
        telegram=tg,
        memory=mem,
        bridge=bridge,
        state_path=tmp_path / "agent_state.json",
        conversations_dir=tmp_path / "conversations",
    )
    return {"runner": runner, "tg": tg, "mem": mem, "bridge": bridge, "tmp_path": tmp_path}


class TestRunOnce:
    def test_no_messages_returns_empty(self, env):
        results = env["runner"].run_once()
        assert results == []
        env["bridge"].invoke.assert_not_called()

    def test_processes_single_message(self, env):
        env["bridge"].invoke.return_value = make_plan(
            tool_calls=[
                ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "hi back"}),
            ],
        )
        env["tg"].enqueue_message("hello")
        results = env["runner"].run_once()

        assert len(results) == 1
        assert results[0]["success"] is True
        env["bridge"].invoke.assert_called_once()
        # Verify the reply was written to outbox
        outbox = env["tg"].get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["text"] == "hi back"

    def test_processes_multiple_messages(self, env):
        env["bridge"].invoke.return_value = make_plan(
            tool_calls=[
                ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "reply"}),
            ],
        )
        env["tg"].enqueue_message("msg1")
        env["tg"].enqueue_message("msg2")
        results = env["runner"].run_once()

        assert len(results) == 2
        assert env["bridge"].invoke.call_count == 2

    def test_passes_user_message_to_bridge(self, env):
        env["bridge"].invoke.return_value = make_plan()
        env["tg"].enqueue_message("specific text", chat_id="my-chat")
        env["runner"].run_once()

        call_kwargs = env["bridge"].invoke.call_args
        assert call_kwargs.kwargs["user_message"] == "specific text"
        assert call_kwargs.kwargs["chat_id"] == "my-chat"


class TestStatePatch:
    def test_applies_state_patch(self, env):
        env["bridge"].invoke.return_value = make_plan(
            state_patch={"topic": "greetings", "count": 1},
        )
        env["tg"].enqueue_message("hello")
        env["runner"].run_once()

        assert env["runner"]._agent_state["topic"] == "greetings"
        # Verify persisted to disk
        saved = json.loads(env["env"]["tmp_path"].joinpath("agent_state.json").read_text()) if False else None
        state_path = env["runner"].state_path
        saved = json.loads(state_path.read_text())
        assert saved["count"] == 1

    def test_state_accumulates_across_messages(self, env):
        env["bridge"].invoke.side_effect = [
            make_plan(state_patch={"a": 1}),
            make_plan(state_patch={"b": 2}),
        ]
        env["tg"].enqueue_message("first")
        env["tg"].enqueue_message("second")
        env["runner"].run_once()

        assert env["runner"]._agent_state == {"a": 1, "b": 2}

    def test_no_state_patch_does_not_write(self, env):
        env["bridge"].invoke.return_value = make_plan()
        env["tg"].enqueue_message("hello")
        env["runner"].run_once()

        # State file should not exist if no patch applied and it didn't exist before
        assert not env["runner"].state_path.exists()


class TestTranscript:
    def test_transcript_written_to_session_file(self, env):
        env["bridge"].invoke.return_value = make_plan(
            message="thinking",
            tool_calls=[
                ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "yo"}),
            ],
        )
        env["tg"].enqueue_message("hello")
        env["runner"].run_once()

        session_file = env["runner"]._session_path
        assert session_file.exists()
        lines = session_file.read_text().strip().split("\n")
        # Should have: user, assistant, tool_results
        assert len(lines) == 3
        assert json.loads(lines[0])["role"] == "user"
        assert json.loads(lines[1])["role"] == "assistant"
        assert json.loads(lines[2])["role"] == "tool_results"

    def test_transcript_passed_to_bridge(self, env):
        env["bridge"].invoke.return_value = make_plan()
        env["tg"].enqueue_message("first")
        env["runner"].run_once()

        env["bridge"].invoke.return_value = make_plan()
        env["tg"].enqueue_message("second")
        env["runner"].run_once()

        # Second call should have transcript from first message
        second_call = env["bridge"].invoke.call_args_list[1]
        transcript = second_call.kwargs["transcript"]
        assert len(transcript) >= 1  # At least the first user message


class TestCloudCodeFailure:
    def test_cloudcode_error_does_not_crash(self, env):
        env["bridge"].invoke.side_effect = CloudCodeError("timeout")
        env["tg"].enqueue_message("hello")
        results = env["runner"].run_once()

        # Should return empty results, not raise
        assert results == []

    def test_continues_after_cloudcode_failure(self, env):
        env["bridge"].invoke.side_effect = [
            CloudCodeError("first fails"),
            make_plan(
                tool_calls=[
                    ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "ok"}),
                ],
            ),
        ]
        env["tg"].enqueue_message("msg1")
        env["tg"].enqueue_message("msg2")
        results = env["runner"].run_once()

        # Only the second message produced results
        assert len(results) == 1
        assert results[0]["success"] is True


class TestMemoryIntegration:
    def test_memory_put_via_plan(self, env):
        env["bridge"].invoke.return_value = make_plan(
            tool_calls=[
                ToolCall(tool_name=ToolName.MEMORY_PUT, args={"text": "remember this", "tags": ["test"]}),
            ],
        )
        env["tg"].enqueue_message("store something")
        env["runner"].run_once()

        latest = env["mem"].memory_get_latest(1)
        assert len(latest) == 1
        assert latest[0]["text"] == "remember this"


class TestLoadState:
    def test_loads_existing_state(self, env):
        state_path = env["runner"].state_path
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps({"existing": "data"}))

        # Create a new runner that should load the state
        runner2 = AgentRunner(
            telegram=env["tg"],
            memory=env["mem"],
            bridge=env["bridge"],
            state_path=state_path,
            conversations_dir=env["runner"].conversations_dir,
        )
        assert runner2._agent_state == {"existing": "data"}

    def test_handles_missing_state_file(self, env):
        assert env["runner"]._agent_state == {}
