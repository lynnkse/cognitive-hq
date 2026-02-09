"""Tests for the inbox socket server."""

import json
import socket
import time
from pathlib import Path
from queue import Queue

import pytest

from src.adapters.inbox_server import InboxServer


def send_raw(socket_path: Path, data: str, timeout: float = 5.0) -> str:
    """Helper: send raw data to the socket and return the response."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(socket_path))
        sock.sendall(data.encode())
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf.decode().strip()
    finally:
        sock.close()


def send_message(socket_path: Path, msg: dict) -> dict:
    """Helper: send a JSON message and return parsed ack."""
    raw = send_raw(socket_path, json.dumps(msg) + "\n")
    return json.loads(raw)


@pytest.fixture
def server(tmp_path):
    """Create and start an InboxServer, stop it after the test."""
    q = Queue()
    sock_path = tmp_path / "agent.sock"
    inbox_path = tmp_path / "inbox.jsonl"
    srv = InboxServer(queue=q, socket_path=sock_path, inbox_path=inbox_path)
    srv.start()
    yield {"server": srv, "queue": q, "socket_path": sock_path, "inbox_path": inbox_path}
    srv.stop()


class TestLifecycle:
    def test_start_creates_socket_file(self, server):
        assert server["socket_path"].exists()

    def test_stop_removes_socket_file(self, tmp_path):
        q = Queue()
        sock_path = tmp_path / "agent.sock"
        srv = InboxServer(queue=q, socket_path=sock_path, inbox_path=tmp_path / "inbox.jsonl")
        srv.start()
        assert sock_path.exists()
        srv.stop()
        assert not sock_path.exists()

    def test_start_cleans_stale_socket(self, tmp_path):
        sock_path = tmp_path / "agent.sock"
        sock_path.write_text("stale")
        q = Queue()
        srv = InboxServer(queue=q, socket_path=sock_path, inbox_path=tmp_path / "inbox.jsonl")
        srv.start()
        # Should have replaced the stale file with a real socket
        assert sock_path.exists()
        srv.stop()


class TestReceiveMessage:
    def test_message_appears_in_queue(self, server):
        msg = {"type": "user_message", "chat_id": "test-chat", "text": "hello"}
        send_message(server["socket_path"], msg)

        assert not server["queue"].empty()
        record = server["queue"].get_nowait()
        assert record["text"] == "hello"
        assert record["chat_id"] == "test-chat"
        assert record["type"] == "user_message"

    def test_message_persisted_to_jsonl(self, server):
        msg = {"type": "user_message", "chat_id": "c1", "text": "persist me"}
        send_message(server["socket_path"], msg)

        lines = server["inbox_path"].read_text().strip().split("\n")
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["text"] == "persist me"
        assert record["chat_id"] == "c1"

    def test_server_assigns_message_id_and_ts(self, server):
        msg = {"text": "no id provided"}
        ack = send_message(server["socket_path"], msg)

        assert ack["status"] == "ok"
        assert "message_id" in ack
        assert "ts" in ack
        assert len(ack["message_id"]) > 0

    def test_ack_message_id_matches_queued_record(self, server):
        msg = {"text": "check ids"}
        ack = send_message(server["socket_path"], msg)

        record = server["queue"].get_nowait()
        assert ack["message_id"] == record["message_id"]
        assert ack["ts"] == record["ts"]

    def test_defaults_for_missing_fields(self, server):
        msg = {"text": "minimal"}
        send_message(server["socket_path"], msg)

        record = server["queue"].get_nowait()
        assert record["type"] == "user_message"
        assert record["chat_id"] == "local-test"

    def test_multiple_sequential_connections(self, server):
        for i in range(5):
            msg = {"text": f"msg-{i}"}
            ack = send_message(server["socket_path"], msg)
            assert ack["status"] == "ok"

        messages = []
        while not server["queue"].empty():
            messages.append(server["queue"].get_nowait())
        assert len(messages) == 5
        assert [m["text"] for m in messages] == [f"msg-{i}" for i in range(5)]


class TestErrorHandling:
    def test_invalid_json_returns_error(self, server):
        raw = send_raw(server["socket_path"], "not json\n")
        resp = json.loads(raw)
        assert resp["status"] == "error"
        assert "Invalid JSON" in resp["error"]

    def test_empty_request_returns_error(self, server):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(5.0)
        try:
            sock.connect(str(server["socket_path"]))
            sock.shutdown(socket.SHUT_WR)
            buf = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
            resp = json.loads(buf.decode().strip())
            assert resp["status"] == "error"
            assert "Empty" in resp["error"]
        finally:
            sock.close()
