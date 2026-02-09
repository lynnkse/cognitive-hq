"""Inbox Client — sends messages to the agent via Unix domain socket.

Usage:
    from src.adapters.inbox_client import send_to_agent
    ack = send_to_agent("hello agent", chat_id="local-test")
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

DEFAULT_SOCKET_PATH = Path("state/agent.sock")


class AgentNotRunningError(Exception):
    """Raised when the agent socket is not available."""


class InboxSendError(Exception):
    """Raised when the server returns an error response."""


def send_to_agent(
    text: str,
    chat_id: str = "local-test",
    socket_path: Path | str = DEFAULT_SOCKET_PATH,
    timeout: float = 5.0,
) -> dict:
    """Send a message to the running agent via Unix domain socket.

    Returns the server's ack dict with message_id and ts.
    Raises AgentNotRunningError if the socket doesn't exist or connection is refused.
    Raises InboxSendError if the server returns an error.
    """
    socket_path = Path(socket_path)

    if not socket_path.exists():
        raise AgentNotRunningError(
            f"Agent socket not found at {socket_path}. Is the agent running?"
        )

    msg = {"type": "user_message", "chat_id": chat_id, "text": text}

    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        sock.connect(str(socket_path))
        sock.sendall((json.dumps(msg) + "\n").encode())

        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk

        response = json.loads(buf.decode().strip())
        if response.get("status") != "ok":
            raise InboxSendError(response.get("error", "Unknown error"))
        return response
    except ConnectionRefusedError as e:
        raise AgentNotRunningError(
            f"Connection refused at {socket_path}. Is the agent running?"
        ) from e
    except FileNotFoundError as e:
        raise AgentNotRunningError(
            f"Agent socket not found at {socket_path}. Is the agent running?"
        ) from e
    finally:
        sock.close()
