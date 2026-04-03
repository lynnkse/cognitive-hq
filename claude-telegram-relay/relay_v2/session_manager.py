#!/usr/bin/env python3
"""
SessionManagerNode — Relay v2

Owns the persistent Claude CLI process. Receives messages from all frontends
via sockets, serializes them into Claude's stdin, and publishes responses.

Sockets:
  user_input.sock   — NDJSON in:  {text, source, user_id, media_path?}
  cli_input.sock    — raw bytes in: keyboard input from CLINode
  display.sock      — raw bytes out: PTY output to CLINode
  claude_response.sock — NDJSON out: {text, source, user_id}

State machine (queue processor):
  IDLE:       keyboard bytes flow freely to Claude's PTY.
              Dequeues next item when available → GENERATING.
  GENERATING: keyboard bytes buffered (not forwarded).
              Waits for sentinel in PTY output → publishes response → IDLE.
"""

import os
import sys
import pty
import fcntl
import termios
import struct
import socket
import threading
import queue
import signal
import glob
import uuid
import re
import json
import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [session_manager] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ANSI escape sequence pattern for stripping from Telegram responses
_ANSI_RE = re.compile(rb"\x1b\[[0-9;]*[mGKHFABCDsuJrHf]|\x1b[=>]|\x1b\[\?[0-9;]*[hl]")


@dataclass
class QueueItem:
    text: str
    source: str       # "telegram" | "proactive"
    user_id: str
    media_path: Optional[str] = None


class SessionManagerNode:

    def __init__(self):
        self.sentinel = f"<<RELAY_END_{uuid.uuid4().hex[:8]}>>"
        self.sentinel_bytes = self.sentinel.encode()

        self.input_queue: queue.Queue[Optional[QueueItem]] = queue.Queue()
        self.state = "IDLE"           # IDLE | GENERATING
        self.current_item: Optional[QueueItem] = None
        self.response_buffer: list[bytes] = []
        self.response_ready = threading.Event()

        # Keyboard bytes buffered while GENERATING
        self.keyboard_buffer: list[bytes] = []
        self.state_lock = threading.Lock()

        self.master_fd: Optional[int] = None
        self.claude_proc: Optional[subprocess.Popen] = None
        self.pty_lock = threading.Lock()

        # CLINode display connection (one at a time)
        self.display_client: Optional[socket.socket] = None
        self.display_lock = threading.Lock()

        # Subscribers to claude_response.sock (RouterNode, etc.)
        self.response_subscribers: list[socket.socket] = []
        self.response_subs_lock = threading.Lock()

        self._running = True
        self._reader_thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Config / system prompt
    # ------------------------------------------------------------------

    def _load_profile(self) -> str:
        try:
            return config.PROFILE_PATH.read_text()
        except Exception:
            return ""

    def _build_system_prompt(self) -> str:
        profile = self._load_profile()
        parts = [
            f"You are operating inside a relay system. "
            f"You MUST end every single response with this exact token on its own line: {self.sentinel}",
            "Do not explain the token. Do not omit it. It is required for message routing.",
        ]
        if config.USER_NAME:
            parts.append(f"You are speaking with {config.USER_NAME}.")
        if config.USER_TIMEZONE:
            parts.append(f"User timezone: {config.USER_TIMEZONE}")
        if profile:
            parts.append(f"\nProfile:\n{profile}")
        parts.append(
            "\nMEMORY MANAGEMENT: When the user shares something worth remembering, "
            "include these tags in your response (processed automatically, hidden from user):\n"
            "[REMEMBER: fact to store]\n"
            "[GOAL: goal text | DEADLINE: optional date]\n"
            "[DONE: search text for completed goal]"
        )
        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Session ID tracking
    # ------------------------------------------------------------------

    def _get_saved_session_id(self) -> Optional[str]:
        try:
            return Path(config.SESSION_ID_FILE).read_text().strip() or None
        except Exception:
            return None

    def _find_newest_session(self) -> Optional[str]:
        """Find the most recently modified session file for this project."""
        project_name = config.PROJECT_DIR.replace("/", "-")
        sessions_dir = Path.home() / ".claude" / "projects" / project_name
        files = sorted(
            sessions_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        if files:
            return files[0].stem
        return None

    def _save_session_id(self, session_id: str):
        Path(config.RELAY_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.SESSION_ID_FILE).write_text(session_id)
        log.info(f"Session ID saved: {session_id[:8]}...")

    def _capture_new_session_id(self):
        """Called 5s after spawning a new (non-resumed) session."""
        time.sleep(5)
        session_id = self._find_newest_session()
        if session_id:
            self._save_session_id(session_id)
        else:
            log.warning("Could not capture new session ID")

    # ------------------------------------------------------------------
    # Claude process lifecycle
    # ------------------------------------------------------------------

    def _spawn_claude(self):
        cmd = [config.CLAUDE_PATH]

        existing_session = self._get_saved_session_id()
        if existing_session:
            cmd += ["--resume", existing_session]
            log.info(f"Resuming session: {existing_session[:8]}...")
        else:
            log.info("Starting new session")
            threading.Thread(target=self._capture_new_session_id, daemon=True).start()

        cmd += ["--append-system-prompt", self._build_system_prompt()]

        # Get current terminal size for PTY
        try:
            size = fcntl.ioctl(sys.stdout.fileno(), termios.TIOCGWINSZ, b"\x00" * 8)
            rows, cols = struct.unpack("HHHH", size)[:2]
        except Exception:
            rows, cols = 24, 80

        master_fd, slave_fd = pty.openpty()
        self._set_pty_size(master_fd, rows, cols)

        # Strip CLAUDECODE to allow nested Claude session
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        proc = subprocess.Popen(
            cmd,
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            cwd=config.PROJECT_DIR,
            env=env,
        )
        os.close(slave_fd)

        with self.pty_lock:
            self.master_fd = master_fd
            self.claude_proc = proc

        log.info(f"Claude spawned (PID: {proc.pid})")

    def _set_pty_size(self, fd: int, rows: int, cols: int):
        try:
            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                        struct.pack("HHHH", rows, cols, 0, 0))
        except Exception:
            pass

    def _handle_claude_exit(self):
        log.warning("Claude process exited — restarting in 2s...")
        time.sleep(2)
        if self._running:
            self._spawn_claude()
            self._reader_thread = threading.Thread(
                target=self._pty_reader_thread, daemon=True
            )
            self._reader_thread.start()

    # ------------------------------------------------------------------
    # PTY reader thread
    # ------------------------------------------------------------------

    def _pty_reader_thread(self):
        """
        Reads Claude's PTY output continuously.
        - Forwards raw bytes to CLINode display, stripping the sentinel.
        - Accumulates response buffer.
        - Signals response_ready when sentinel found.
        """
        holdback = b""
        sentinel_len = len(self.sentinel_bytes)

        while self._running:
            try:
                chunk = os.read(self.master_fd, 4096)
            except OSError:
                break

            if not chunk:
                break

            data = holdback + chunk

            idx = data.find(self.sentinel_bytes)
            if idx != -1:
                # Forward everything before the sentinel
                before = data[:idx]
                if before:
                    self._forward_display(before)
                    self.response_buffer.append(before)

                # Signal response complete
                self.response_ready.set()

                # Remainder after sentinel becomes next holdback
                holdback = data[idx + sentinel_len:]
            else:
                # No sentinel yet — forward all but the last (sentinel_len-1) bytes
                # to avoid splitting the sentinel across reads
                safe = max(0, len(data) - (sentinel_len - 1))
                if safe > 0:
                    safe_bytes = data[:safe]
                    self._forward_display(safe_bytes)
                    self.response_buffer.append(safe_bytes)
                holdback = data[safe:]

        log.warning("PTY reader exiting")
        self._handle_claude_exit()

    def _forward_display(self, data: bytes):
        with self.display_lock:
            if self.display_client:
                try:
                    self.display_client.sendall(data)
                except Exception:
                    self.display_client = None

    # ------------------------------------------------------------------
    # Queue processor thread (state machine)
    # ------------------------------------------------------------------

    def _queue_processor_thread(self):
        """
        Processes queued messages from Telegram / Proactive.
        Waits for sentinel after each injection before processing next.
        """
        while self._running:
            item = self.input_queue.get()
            if item is None:
                break

            with self.state_lock:
                self.state = "GENERATING"
                self.current_item = item
                self.response_buffer = []
            self.response_ready.clear()

            log.info(f"Processing queued message from {item.source}: {item.text[:50]}...")

            # Inject message into Claude's stdin via PTY
            try:
                os.write(self.master_fd, (item.text + "\n").encode())
            except OSError:
                log.error("Failed to write queued message to PTY")
                with self.state_lock:
                    self.state = "IDLE"
                    self.current_item = None
                self._flush_keyboard_buffer()
                continue

            # Wait for sentinel (response complete)
            self.response_ready.wait()

            response_bytes = b"".join(self.response_buffer)
            self._publish_response(item, response_bytes)

            with self.state_lock:
                self.state = "IDLE"
                self.current_item = None

            # Flush any keyboard bytes that arrived while GENERATING
            self._flush_keyboard_buffer()

    def _flush_keyboard_buffer(self):
        with self.state_lock:
            buffered = self.keyboard_buffer[:]
            self.keyboard_buffer = []
        for chunk in buffered:
            self._write_to_pty(chunk)

    def _write_to_pty(self, data: bytes):
        try:
            os.write(self.master_fd, data)
        except OSError:
            pass

    # ------------------------------------------------------------------
    # Response publishing
    # ------------------------------------------------------------------

    def _publish_response(self, item: QueueItem, response_bytes: bytes):
        clean = _ANSI_RE.sub(b"", response_bytes).decode("utf-8", errors="replace").strip()

        # Strip memory tags for delivery (MemoryNode reads them before stripping)
        # For now, pass raw clean text — MemoryNode will be added in phase 2
        payload = json.dumps({
            "text": clean,
            "source": item.source,
            "user_id": item.user_id,
        }) + "\n"

        payload_bytes = payload.encode()

        with self.response_subs_lock:
            dead = []
            for conn in self.response_subscribers:
                try:
                    conn.sendall(payload_bytes)
                except Exception:
                    dead.append(conn)
            for conn in dead:
                self.response_subscribers.remove(conn)
                log.info("Removed dead response subscriber")

    # ------------------------------------------------------------------
    # Socket servers
    # ------------------------------------------------------------------

    def _user_input_server_thread(self):
        """Accepts NDJSON messages from Telegram / Proactive nodes."""
        sock_path = config.USER_INPUT_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(5)
        log.info(f"user_input.sock listening")

        while self._running:
            try:
                conn, _ = server.accept()
                threading.Thread(
                    target=self._handle_input_conn, args=(conn,), daemon=True
                ).start()
            except Exception:
                break

    def _handle_input_conn(self, conn: socket.socket):
        buf = b""
        with conn:
            while True:
                try:
                    data = conn.recv(4096)
                except Exception:
                    break
                if not data:
                    break
                buf += data
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    if not line.strip():
                        continue
                    try:
                        msg = json.loads(line)
                        self.input_queue.put(QueueItem(
                            text=msg["text"],
                            source=msg.get("source", "unknown"),
                            user_id=msg.get("user_id", ""),
                            media_path=msg.get("media_path"),
                        ))
                    except (json.JSONDecodeError, KeyError) as e:
                        log.warning(f"Bad input message: {e}")

    def _cli_input_server_thread(self):
        """Accepts raw keyboard bytes from CLINode."""
        sock_path = config.CLI_INPUT_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)
        log.info(f"cli_input.sock listening")

        while self._running:
            try:
                conn, _ = server.accept()
                log.info("CLINode keyboard connected")
                threading.Thread(
                    target=self._handle_cli_input, args=(conn,), daemon=True
                ).start()
            except Exception:
                break

    def _handle_cli_input(self, conn: socket.socket):
        """
        Forward keyboard bytes to Claude PTY, buffering during GENERATING.
        Control messages are prefixed with 0x00 and are JSON lines:
          \x00{"type":"resize","rows":N,"cols":N}\n
        """
        buf = b""
        with conn:
            while True:
                try:
                    data = conn.recv(256)
                except Exception:
                    break
                if not data:
                    break

                buf += data

                # Extract and handle control messages (0x00-prefixed JSON lines)
                while b"\x00" in buf:
                    pre, _, rest = buf.partition(b"\x00")
                    # Forward any bytes before the control marker
                    if pre:
                        self._route_keyboard_bytes(pre)
                    # Find end of control message
                    if b"\n" in rest:
                        line, _, buf = rest.partition(b"\n")
                        try:
                            msg = json.loads(line)
                            if msg.get("type") == "resize":
                                with self.pty_lock:
                                    if self.master_fd is not None:
                                        self._set_pty_size(
                                            self.master_fd,
                                            msg["rows"],
                                            msg["cols"],
                                        )
                        except (json.JSONDecodeError, KeyError):
                            pass
                    else:
                        # Incomplete control message — wait for more data
                        buf = b"\x00" + rest
                        break
                else:
                    # No control marker — all keyboard bytes
                    if buf:
                        self._route_keyboard_bytes(buf)
                        buf = b""

        log.info("CLINode keyboard disconnected")

    def _route_keyboard_bytes(self, data: bytes):
        """Forward keyboard bytes to PTY, or buffer if GENERATING."""
        with self.state_lock:
            generating = self.state == "GENERATING"
            if generating:
                self.keyboard_buffer.append(data)
            else:
                self._write_to_pty(data)

    def _display_server_thread(self):
        """Streams raw PTY output to CLINode (one connection at a time)."""
        sock_path = config.DISPLAY_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)
        log.info(f"display.sock listening")

        while self._running:
            try:
                conn, _ = server.accept()
                log.info("CLINode display connected")
                with self.display_lock:
                    if self.display_client:
                        try:
                            self.display_client.close()
                        except Exception:
                            pass
                    self.display_client = conn
            except Exception:
                break

    def _response_server_thread(self):
        """Accepts subscribers on claude_response.sock (RouterNode, etc.)."""
        sock_path = config.CLAUDE_RESPONSE_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(5)
        log.info(f"claude_response.sock listening")

        while self._running:
            try:
                conn, _ = server.accept()
                log.info("Response subscriber connected")
                with self.response_subs_lock:
                    self.response_subscribers.append(conn)
            except Exception:
                break

    # ------------------------------------------------------------------
    # Lock file
    # ------------------------------------------------------------------

    def _acquire_lock(self) -> bool:
        lock = Path(config.LOCK_FILE)
        if lock.exists():
            try:
                pid = int(lock.read_text().strip())
                os.kill(pid, 0)  # check if process exists
                log.error(f"Another SessionManagerNode running (PID {pid})")
                return False
            except (ProcessLookupError, ValueError):
                log.info("Stale lock found, taking over")
        Path(config.RELAY_DIR).mkdir(parents=True, exist_ok=True)
        lock.write_text(str(os.getpid()))
        return True

    def _release_lock(self):
        try:
            Path(config.LOCK_FILE).unlink()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Startup / shutdown
    # ------------------------------------------------------------------

    def run(self):
        if not self._acquire_lock():
            sys.exit(1)

        os.makedirs(config.SOCKET_DIR, exist_ok=True)
        os.makedirs(config.RELAY_DIR, exist_ok=True)

        self._spawn_claude()

        self._reader_thread = threading.Thread(
            target=self._pty_reader_thread, daemon=True
        )

        threads = [
            self._reader_thread,
            threading.Thread(target=self._queue_processor_thread, daemon=True),
            threading.Thread(target=self._user_input_server_thread, daemon=True),
            threading.Thread(target=self._cli_input_server_thread, daemon=True),
            threading.Thread(target=self._display_server_thread, daemon=True),
            threading.Thread(target=self._response_server_thread, daemon=True),
        ]
        for t in threads:
            t.start()

        signal.signal(signal.SIGINT, self._shutdown)
        signal.signal(signal.SIGTERM, self._shutdown)

        log.info("SessionManagerNode running — press Ctrl+C to stop")

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            self._shutdown()

    def _shutdown(self, *_):
        log.info("Shutting down...")
        self._running = False
        self.input_queue.put(None)

        if self.claude_proc:
            try:
                self.claude_proc.terminate()
            except Exception:
                pass

        for sock_path in [
            config.USER_INPUT_SOCK,
            config.CLI_INPUT_SOCK,
            config.DISPLAY_SOCK,
            config.CLAUDE_RESPONSE_SOCK,
        ]:
            try:
                os.unlink(sock_path)
            except Exception:
                pass

        self._release_lock()
        sys.exit(0)


if __name__ == "__main__":
    SessionManagerNode().run()
