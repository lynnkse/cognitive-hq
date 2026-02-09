"""Inbox Server — Unix domain socket server for receiving messages.

Listens on a Unix domain socket. Each connection:
1. Reads one newline-delimited JSON message
2. Validates and enriches it (adds ts, message_id)
3. Persists to inbox JSONL (single writer, no race condition)
4. Pushes onto a thread-safe queue for the agent runner
5. Sends back an ack JSON + newline
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import uuid
from pathlib import Path
from queue import Queue
from typing import Any

from src.runner.time_utils import utc_now

logger = logging.getLogger(__name__)

DEFAULT_SOCKET_PATH = Path("state/agent.sock")
DEFAULT_INBOX_PATH = Path("state/telegram_inbox.jsonl")


class InboxServer:
    """Unix domain socket server that feeds a Queue with incoming messages."""

    def __init__(
        self,
        queue: Queue,
        socket_path: Path | str = DEFAULT_SOCKET_PATH,
        inbox_path: Path | str = DEFAULT_INBOX_PATH,
    ):
        self._queue = queue
        self.socket_path = Path(socket_path)
        self.inbox_path = Path(inbox_path)
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        """Start the socket server in a daemon thread."""
        if self._running:
            return

        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        self.inbox_path.parent.mkdir(parents=True, exist_ok=True)

        # Clean up stale socket file
        if self.socket_path.exists():
            self.socket_path.unlink()

        self._server_socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server_socket.bind(str(self.socket_path))
        self._server_socket.listen(5)
        self._server_socket.settimeout(1.0)

        self._running = True
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        logger.info("Inbox server started on %s", self.socket_path)

    def stop(self) -> None:
        """Stop the socket server and clean up."""
        self._running = False
        if self._server_socket:
            self._server_socket.close()
            self._server_socket = None
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self.socket_path.exists():
            self.socket_path.unlink()
        logger.info("Inbox server stopped")

    def _accept_loop(self) -> None:
        """Accept connections in a loop until stopped."""
        while self._running:
            try:
                conn, _ = self._server_socket.accept()
                self._handle_connection(conn)
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    logger.exception("Socket accept error")
                break

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle a single client connection."""
        try:
            conn.settimeout(5.0)
            data = self._recv_line(conn)
            if not data:
                self._send_error(conn, "Empty request")
                return

            msg = json.loads(data)
            record = self._enrich_and_persist(msg)
            self._queue.put(record)

            ack = {
                "status": "ok",
                "message_id": record["message_id"],
                "ts": record["ts"],
            }
            conn.sendall((json.dumps(ack) + "\n").encode())
        except json.JSONDecodeError as e:
            self._send_error(conn, f"Invalid JSON: {e}")
        except Exception as e:
            logger.exception("Error handling connection")
            self._send_error(conn, str(e))
        finally:
            conn.close()

    def _recv_line(self, conn: socket.socket) -> str:
        """Read bytes until newline or connection close."""
        buf = b""
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                return buf.decode().strip()
            buf += chunk
            if b"\n" in buf:
                return buf.split(b"\n", 1)[0].decode().strip()

    def _enrich_and_persist(self, msg: dict[str, Any]) -> dict[str, Any]:
        """Add server-assigned fields and append to inbox JSONL."""
        record: dict[str, Any] = {
            "ts": utc_now(),
            "type": msg.get("type", "user_message"),
            "chat_id": msg.get("chat_id", "local-test"),
            "message_id": str(uuid.uuid4()),
            "text": msg.get("text", ""),
        }
        with open(self.inbox_path, "a") as f:
            f.write(json.dumps(record) + "\n")
        return record

    @staticmethod
    def _send_error(conn: socket.socket, error: str) -> None:
        """Send an error response."""
        try:
            resp = {"status": "error", "error": error}
            conn.sendall((json.dumps(resp) + "\n").encode())
        except OSError:
            pass
