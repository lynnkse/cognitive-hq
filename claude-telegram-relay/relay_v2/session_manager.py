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
              Polls session JSONL for new assistant entry → publishes → IDLE.

Response detection strategy:
  Claude's interactive TUI does NOT echo all response text to the PTY (it
  suppresses control tokens like sentinels). Instead, we watch the session
  JSONL file which always contains the complete, clean response text once
  a turn is finished. No sentinel needed.
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
import signal as signal_module
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

# How long to wait for Claude's response before giving up (seconds)
_RESPONSE_TIMEOUT = 180
# How often to poll the session JSONL (seconds)
_POLL_INTERVAL = 0.5


@dataclass
class QueueItem:
    text: str
    source: str       # "telegram" | "proactive"
    user_id: str
    media_path: Optional[str] = None


class SessionManagerNode:

    def __init__(self):
        self.input_queue: queue.Queue[Optional[QueueItem]] = queue.Queue()
        self.state = "IDLE"           # IDLE | GENERATING
        self.current_item: Optional[QueueItem] = None

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

        # Tracked after Claude spawns so JSONL watcher knows where to look
        self.current_session_id: Optional[str] = None
        # Epoch time of most recent Claude spawn — used to filter session files
        self._spawn_time: float = 0.0

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
        parts = []
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

    def _find_newest_session(self, not_before: float) -> Optional[str]:
        project_name = config.PROJECT_DIR.replace("/", "-")
        sessions_dir = Path.home() / ".claude" / "projects" / project_name
        files = sorted(
            sessions_dir.glob("*.jsonl"),
            key=lambda f: f.stat().st_mtime,
            reverse=True,
        )
        for f in files:
            if f.stat().st_mtime > not_before:
                return f.stem
        return None

    def _save_session_id(self, session_id: str):
        Path(config.RELAY_DIR).mkdir(parents=True, exist_ok=True)
        Path(config.SESSION_ID_FILE).write_text(session_id)
        log.info(f"Session ID saved: {session_id[:8]}...")

    def _capture_new_session_id(self, spawn_time: float):
        deadline = spawn_time + 30
        while time.time() < deadline:
            time.sleep(2)
            session_id = self._find_newest_session(not_before=spawn_time)
            if session_id:
                self._save_session_id(session_id)
                self.current_session_id = session_id
                log.info(f"New session captured: {session_id[:8]}...")
                return
        log.warning("Could not capture new session ID within 30s")

    def _get_session_file_path(self, session_id: str) -> Path:
        project_name = config.PROJECT_DIR.replace("/", "-")
        sessions_dir = Path.home() / ".claude" / "projects" / project_name
        return sessions_dir / f"{session_id}.jsonl"

    # ------------------------------------------------------------------
    # Claude process lifecycle
    # ------------------------------------------------------------------

    def _spawn_claude(self):
        cmd = [config.CLAUDE_PATH]

        existing_session = self._get_saved_session_id()
        self._spawn_time = time.time()
        if existing_session:
            cmd += ["--resume", existing_session]
            self.current_session_id = existing_session
            log.info(f"Resuming session: {existing_session[:8]}...")
        else:
            log.info("Starting new session (ID captured on first response)")

        system_prompt = self._build_system_prompt()
        if system_prompt.strip():
            cmd += ["--append-system-prompt", system_prompt]

        rows, cols = 24, 80
        master_fd, slave_fd = pty.openpty()
        self._set_pty_size(master_fd, rows, cols)

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
        if self.claude_proc and self.claude_proc.poll() is None:
            try:
                os.kill(self.claude_proc.pid, signal_module.SIGWINCH)
            except Exception:
                pass

    def _handle_claude_exit(self):
        log.warning("Claude process exited — restarting in 2s...")
        time.sleep(2)
        if self._running:
            self.current_session_id = None  # will be re-captured or resumed
            self._spawn_claude()
            self._reader_thread = threading.Thread(
                target=self._pty_reader_thread, daemon=True
            )
            self._reader_thread.start()

    # ------------------------------------------------------------------
    # PTY reader thread — display only, no response detection
    # ------------------------------------------------------------------

    def _pty_reader_thread(self):
        """
        Reads Claude's PTY output and forwards raw bytes to CLINode display.
        Response detection is done via JSONL polling, not PTY scanning.
        """
        while self._running:
            try:
                chunk = os.read(self.master_fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            self._forward_display(chunk)

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
    # JSONL response detection
    # ------------------------------------------------------------------

    def _read_new_assistant_entry(self, session_file: Path, offset: int) -> Optional[str]:
        """Read the first complete assistant text entry after `offset` bytes."""
        try:
            if not session_file.exists() or session_file.stat().st_size <= offset:
                return None
            with open(session_file, "r", encoding="utf-8", errors="replace") as f:
                f.seek(offset)
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        msg = obj.get("message", {})
                        if msg.get("role") != "assistant":
                            continue
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            # Skip intermediate messages that still have tool_use —
                            # Claude hasn't finished yet. Only the final assistant
                            # message (text only, no pending tool calls) is the reply.
                            if any(c.get("type") == "tool_use" for c in content):
                                continue
                            text = "\n".join(
                                c.get("text", "")
                                for c in content
                                if c.get("type") == "text"
                            )
                        else:
                            text = str(content)
                        if text.strip():
                            return text.strip()
                    except (json.JSONDecodeError, AttributeError):
                        continue
        except Exception:
            pass
        return None

    def _sessions_dir(self) -> Path:
        project_name = config.PROJECT_DIR.replace("/", "-")
        return Path.home() / ".claude" / "projects" / project_name

    def _wait_for_jsonl_response(
        self,
        session_file: Optional[Path],
        initial_size: int,
    ) -> str:
        """
        Poll for a new complete assistant text entry.

        If session_file is known, poll it directly.
        If session_file is None (new session, file not yet created), scan all
        session files modified after _spawn_time — Claude creates the JSONL on
        the first exchange, not at startup.  Once found, save the session ID.
        """
        deadline = time.time() + _RESPONSE_TIMEOUT

        if session_file is not None:
            # Known session — poll the specific file.
            while time.time() < deadline and self._running:
                time.sleep(_POLL_INTERVAL)
                text = self._read_new_assistant_entry(session_file, initial_size)
                if text:
                    log.info(f"Got response from JSONL ({len(text)} chars)")
                    return text
        else:
            # Unknown session — scan all files newer than spawn time.
            sessions_dir = self._sessions_dir()
            # Baseline: current sizes of all existing files.
            try:
                baseline = {
                    f: f.stat().st_size
                    for f in sessions_dir.glob("*.jsonl")
                }
            except Exception:
                baseline = {}

            while time.time() < deadline and self._running:
                time.sleep(_POLL_INTERVAL)
                try:
                    for f in sessions_dir.glob("*.jsonl"):
                        # Only consider files created/modified after spawn.
                        if f.stat().st_mtime <= self._spawn_time:
                            continue
                        offset = baseline.get(f, 0)
                        text = self._read_new_assistant_entry(f, offset)
                        if text:
                            sid = f.stem
                            self._save_session_id(sid)
                            self.current_session_id = sid
                            log.info(
                                f"Session ID captured on first response: {sid[:8]}..."
                            )
                            log.info(f"Got response from JSONL ({len(text)} chars)")
                            return text
                except Exception as e:
                    log.warning(f"Session scan error: {e}")

        log.error("Timeout waiting for JSONL response")
        return "(response timed out — please try again)"

    # ------------------------------------------------------------------
    # Queue processor thread (state machine)
    # ------------------------------------------------------------------

    def _queue_processor_thread(self):
        while self._running:
            item = self.input_queue.get()
            if item is None:
                break

            with self.state_lock:
                self.state = "GENERATING"
                self.current_item = item

            log.info(f"Processing message from {item.source}: {item.text[:50]!r}")

            # If we know the session file, record its current size so we only
            # read entries written AFTER this message. If session_id is unknown
            # (first exchange on a new session), pass None — _wait_for_jsonl_response
            # will scan all files and capture the ID from the first response.
            if self.current_session_id:
                session_file: Optional[Path] = self._get_session_file_path(self.current_session_id)
                try:
                    initial_size = session_file.stat().st_size if session_file.exists() else 0
                except Exception:
                    initial_size = 0
            else:
                session_file = None
                initial_size = 0

            # Inject message via PTY.
            # Claude's TUI runs in raw terminal mode: Enter = \r (not \n).
            try:
                os.write(self.master_fd, (item.text + "\r").encode())
            except OSError:
                log.error("Failed to write message to PTY")
                with self.state_lock:
                    self.state = "IDLE"
                    self.current_item = None
                self._flush_keyboard_buffer()
                continue

            # Poll JSONL for Claude's response.
            response_text = self._wait_for_jsonl_response(session_file, initial_size)
            self._publish_response(item, response_text)

            with self.state_lock:
                self.state = "IDLE"
                self.current_item = None
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

    def _publish_response(self, item: QueueItem, response_text: str):
        # Phase 2 (MemoryNode) will intercept here to extract [REMEMBER] tags
        # before this payload reaches TelegramNode.
        payload = json.dumps({
            "text": response_text,
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

        log.info(f"Published response to {len(self.response_subscribers)} subscriber(s)")

    # ------------------------------------------------------------------
    # Socket servers
    # ------------------------------------------------------------------

    def _user_input_server_thread(self):
        sock_path = config.USER_INPUT_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(5)
        log.info("user_input.sock listening")

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
        sock_path = config.CLI_INPUT_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)
        log.info("cli_input.sock listening")

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

                while b"\x00" in buf:
                    pre, _, rest = buf.partition(b"\x00")
                    if pre:
                        self._route_keyboard_bytes(pre)
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
                        buf = b"\x00" + rest
                        break
                else:
                    if buf:
                        self._route_keyboard_bytes(buf)
                        buf = b""

        log.info("CLINode keyboard disconnected")

    def _route_keyboard_bytes(self, data: bytes):
        with self.state_lock:
            generating = self.state == "GENERATING"
            if generating:
                self.keyboard_buffer.append(data)
            else:
                self._write_to_pty(data)

    def _display_server_thread(self):
        sock_path = config.DISPLAY_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(1)
        log.info("display.sock listening")

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
        sock_path = config.CLAUDE_RESPONSE_SOCK
        if os.path.exists(sock_path):
            os.unlink(sock_path)

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(sock_path)
        server.listen(5)
        log.info("claude_response.sock listening")

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
                os.kill(pid, 0)
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

        signal_module.signal(signal_module.SIGINT, self._shutdown)
        signal_module.signal(signal_module.SIGTERM, self._shutdown)

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
