"""Tests for the inbox socket client."""

import json
from pathlib import Path
from queue import Queue

import pytest

from src.adapters.inbox_client import AgentNotRunningError, InboxSendError, send_to_agent
from src.adapters.inbox_server import InboxServer


@pytest.fixture
def running_agent(tmp_path):
    """Start a real InboxServer to test the client against."""
    q = Queue()
    sock_path = tmp_path / "agent.sock"
    inbox_path = tmp_path / "inbox.jsonl"
    srv = InboxServer(queue=q, socket_path=sock_path, inbox_path=inbox_path)
    srv.start()
    yield {"server": srv, "queue": q, "socket_path": sock_path}
    srv.stop()


class TestSendToAgent:
    def test_send_and_receive_ack(self, running_agent):
        ack = send_to_agent(
            "hello agent",
            chat_id="test-chat",
            socket_path=running_agent["socket_path"],
        )
        assert ack["status"] == "ok"
        assert "message_id" in ack
        assert "ts" in ack

        record = running_agent["queue"].get_nowait()
        assert record["text"] == "hello agent"
        assert record["chat_id"] == "test-chat"

    def test_default_chat_id(self, running_agent):
        send_to_agent("hi", socket_path=running_agent["socket_path"])
        record = running_agent["queue"].get_nowait()
        assert record["chat_id"] == "local-test"


class TestAgentNotRunning:
    def test_no_socket_file(self, tmp_path):
        with pytest.raises(AgentNotRunningError, match="not found"):
            send_to_agent("hello", socket_path=tmp_path / "nonexistent.sock")

    def test_stale_socket_file(self, tmp_path):
        stale = tmp_path / "stale.sock"
        stale.write_text("not a real socket")
        with pytest.raises(AgentNotRunningError, match="refused|not found"):
            send_to_agent("hello", socket_path=stale)
