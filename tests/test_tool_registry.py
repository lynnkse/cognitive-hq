"""Tests for the tool registry."""

import pytest

from src.adapters.memory_emulator import MemoryEmulator
from src.adapters.telegram_emulator import TelegramEmulator
from src.adapters.tool_registry import ToolExecutionError, ToolRegistry
from src.runner.plan_schema import ToolCall, ToolName


@pytest.fixture
def registry(tmp_path):
    """Create a ToolRegistry backed by temp files."""
    tg = TelegramEmulator(
        inbox_path=tmp_path / "inbox.jsonl",
        outbox_path=tmp_path / "outbox.jsonl",
    )
    mem = MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")
    return ToolRegistry(telegram=tg, memory=mem)


@pytest.fixture
def tg(tmp_path):
    return TelegramEmulator(
        inbox_path=tmp_path / "inbox.jsonl",
        outbox_path=tmp_path / "outbox.jsonl",
    )


@pytest.fixture
def mem(tmp_path):
    return MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")


class TestExecuteSingle:
    def test_telegram_send_message(self, registry):
        tc = ToolCall(
            tool_name=ToolName.TELEGRAM_SEND_MESSAGE,
            args={"chat_id": "c1", "text": "hello"},
        )
        result = registry.execute(tc)
        assert result["type"] == "agent_message"
        assert result["text"] == "hello"

    def test_memory_put(self, registry):
        tc = ToolCall(
            tool_name=ToolName.MEMORY_PUT,
            args={"text": "a note", "tags": ["test"]},
        )
        result = registry.execute(tc)
        assert result["text"] == "a note"
        assert result["tags"] == ["test"]
        assert "id" in result

    def test_memory_search(self, registry):
        # Put something first
        registry.execute(ToolCall(
            tool_name=ToolName.MEMORY_PUT,
            args={"text": "python is great"},
        ))
        tc = ToolCall(
            tool_name=ToolName.MEMORY_SEARCH,
            args={"query": "python", "k": 5},
        )
        result = registry.execute(tc)
        assert len(result) == 1
        assert "python" in result[0]["text"]

    def test_memory_get_latest(self, registry):
        registry.execute(ToolCall(
            tool_name=ToolName.MEMORY_PUT,
            args={"text": "entry one"},
        ))
        tc = ToolCall(
            tool_name=ToolName.MEMORY_GET_LATEST,
            args={"n": 10},
        )
        result = registry.execute(tc)
        assert len(result) == 1
        assert result[0]["text"] == "entry one"

    def test_bad_args_raises(self, registry):
        tc = ToolCall(
            tool_name=ToolName.TELEGRAM_SEND_MESSAGE,
            args={"wrong_param": "oops"},
        )
        with pytest.raises(ToolExecutionError, match="Bad args"):
            registry.execute(tc)


class TestExecuteAll:
    def test_multiple_tools_in_order(self, registry):
        calls = [
            ToolCall(tool_name=ToolName.MEMORY_PUT, args={"text": "remember this"}),
            ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "done"}),
        ]
        results = registry.execute_all(calls)
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[0]["tool_name"] == "memory_put"
        assert results[1]["success"] is True
        assert results[1]["tool_name"] == "telegram_send_message"

    def test_empty_list(self, registry):
        assert registry.execute_all([]) == []

    def test_failure_continues_to_next(self, registry):
        calls = [
            ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"bad": "args"}),
            ToolCall(tool_name=ToolName.TELEGRAM_SEND_MESSAGE, args={"chat_id": "c1", "text": "ok"}),
        ]
        results = registry.execute_all(calls)
        assert len(results) == 2
        assert results[0]["success"] is False
        assert "error" in results[0]
        assert results[1]["success"] is True

    def test_results_contain_args(self, registry):
        calls = [
            ToolCall(tool_name=ToolName.MEMORY_PUT, args={"text": "note"}),
        ]
        results = registry.execute_all(calls)
        assert results[0]["args"] == {"text": "note"}


class TestIntegrationRoundTrip:
    def test_plan_to_execution(self, tmp_path):
        """Simulate dispatching a full CloudCode plan through the registry."""
        tg = TelegramEmulator(
            inbox_path=tmp_path / "inbox.jsonl",
            outbox_path=tmp_path / "outbox.jsonl",
        )
        mem = MemoryEmulator(store_path=tmp_path / "memory" / "store.jsonl")
        reg = ToolRegistry(telegram=tg, memory=mem)

        # Simulate a plan that stores a preference and replies
        calls = [
            ToolCall(
                tool_name=ToolName.MEMORY_PUT,
                args={"text": "User prefers Python", "tags": ["preference"], "source": "conversation", "metadata": {}},
            ),
            ToolCall(
                tool_name=ToolName.TELEGRAM_SEND_MESSAGE,
                args={"chat_id": "local-test", "text": "Got it!"},
            ),
        ]
        results = reg.execute_all(calls)
        assert all(r["success"] for r in results)

        # Verify side effects
        assert mem.memory_get_latest(1)[0]["text"] == "User prefers Python"
        outbox = tg.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["text"] == "Got it!"
