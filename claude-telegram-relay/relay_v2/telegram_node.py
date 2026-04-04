#!/usr/bin/env python3
"""
TelegramNode — Relay v2

Bridges Telegram ↔ SessionManagerNode.

Inbound (Telegram → SessionManager):
  - Text messages → send NDJSON to user_input.sock
  - Voice messages → download → Groq transcription → user_input.sock
  - Photos/documents → download to uploads dir → user_input.sock with media_path

Outbound (SessionManager → Telegram):
  - Subscribes to claude_response.sock (persistent connection)
  - Receives NDJSON {text, source, user_id}
  - Strips memory tags ([REMEMBER], [GOAL], [DONE])
  - Splits at 4096-char Telegram limit
  - Sends to the user

Typing keepalive: sends "typing" action every 4s while waiting for response.
Media cleanup: deletes downloaded files after response delivered.
"""

import asyncio
import json
import logging
import os
import re
import socket
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [telegram_node] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Memory tag stripping ──────────────────────────────────────────────────────

_TAG_RE = re.compile(
    r"\[REMEMBER:[^\]]+\]"
    r"|\[GOAL:[^\]]+\]"
    r"|\[DONE:[^\]]+\]",
    re.IGNORECASE,
)


def _strip_memory_tags(text: str) -> str:
    return _TAG_RE.sub("", text).strip()


# ── Telegram 4096-char splitter ───────────────────────────────────────────────

_MAX_TELEGRAM = 4000


def _split_message(text: str) -> list[str]:
    if len(text) <= _MAX_TELEGRAM:
        return [text]
    chunks = []
    remaining = text
    while remaining:
        if len(remaining) <= _MAX_TELEGRAM:
            chunks.append(remaining)
            break
        split = remaining.rfind("\n\n", 0, _MAX_TELEGRAM)
        if split == -1:
            split = remaining.rfind("\n", 0, _MAX_TELEGRAM)
        if split == -1:
            split = remaining.rfind(" ", 0, _MAX_TELEGRAM)
        if split == -1:
            split = _MAX_TELEGRAM
        chunks.append(remaining[:split])
        remaining = remaining[split:].lstrip()
    return chunks


# ── Voice transcription (Groq) ────────────────────────────────────────────────

async def _transcribe_voice(audio_bytes: bytes) -> str:
    provider = config.get("VOICE_PROVIDER")
    if not provider:
        return ""
    if provider == "groq":
        return await _transcribe_groq(audio_bytes)
    log.warning(f"Unknown VOICE_PROVIDER: {provider}")
    return ""


async def _transcribe_groq(audio_bytes: bytes) -> str:
    groq_key = config.get("GROQ_API_KEY")
    if not groq_key:
        log.warning("GROQ_API_KEY not set")
        return ""
    try:
        from groq import AsyncGroq
        client = AsyncGroq(api_key=groq_key)
        result = await client.audio.transcriptions.create(
            file=("voice.ogg", audio_bytes),
            model="whisper-large-v3-turbo",
        )
        return result.text.strip()
    except Exception as e:
        log.error(f"Groq transcription error: {e}")
        return ""


# ── SessionManager socket helpers ─────────────────────────────────────────────

def _send_to_session_manager(text: str, source: str, user_id: str, media_path: Optional[str] = None):
    """Send one NDJSON message to user_input.sock (fire-and-forget)."""
    msg: dict = {"text": text, "source": source, "user_id": user_id}
    if media_path:
        msg["media_path"] = media_path
    payload = (json.dumps(msg) + "\n").encode()
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(config.USER_INPUT_SOCK)
        sock.sendall(payload)
        sock.close()
    except Exception as e:
        log.error(f"Failed to send to session manager: {e}")


# ── Response subscriber ───────────────────────────────────────────────────────

class ResponseSubscriber:
    """
    Maintains a persistent connection to claude_response.sock.
    Runs in a background thread, puts decoded responses onto an asyncio queue.
    """

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._queue: asyncio.Queue[dict] = asyncio.Queue()
        self._thread = threading.Thread(target=self._reader_thread, daemon=True)
        self._thread.start()

    def _reader_thread(self):
        while True:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(config.CLAUDE_RESPONSE_SOCK)
                log.info("Connected to claude_response.sock")
                buf = b""
                while True:
                    try:
                        data = sock.recv(4096)
                    except Exception:
                        break
                    if not data:
                        break
                    buf += data
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            msg = json.loads(line)
                            self._loop.call_soon_threadsafe(
                                self._queue.put_nowait, msg
                            )
                        except json.JSONDecodeError as e:
                            log.warning(f"Bad response JSON: {e}")
            except Exception as e:
                log.warning(f"claude_response.sock error: {e} — retrying in 3s")
            finally:
                try:
                    sock.close()
                except Exception:
                    pass
            time.sleep(3)

    async def get(self) -> dict:
        return await self._queue.get()


# ── Core handler logic ────────────────────────────────────────────────────────

AUTHORIZED_USER_ID = config.get("TELEGRAM_USER_ID")
UPLOADS_DIR = Path(config.RELAY_DIR) / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _is_authorized(update: Update) -> bool:
    if not AUTHORIZED_USER_ID:
        return True
    return str(update.effective_user.id) == AUTHORIZED_USER_ID


async def _typing_keepalive(update: Update, context: ContextTypes.DEFAULT_TYPE, stop_event: asyncio.Event):
    """Send typing action every 4s until stop_event is set."""
    while not stop_event.is_set():
        try:
            await update.effective_message.reply_chat_action("typing")
        except Exception:
            pass
        try:
            await asyncio.wait_for(asyncio.shield(stop_event.wait()), timeout=4.0)
        except asyncio.TimeoutError:
            pass


async def _wait_for_response(subscriber: ResponseSubscriber, source: str) -> str:
    """Wait for next response from SessionManager with matching source."""
    while True:
        msg = await subscriber.get()
        if msg.get("source") == source:
            return msg.get("text", "")


async def _handle_and_reply(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    subscriber: ResponseSubscriber,
    text: str,
    source: str = "telegram",
    media_path: Optional[str] = None,
):
    """Common handler: send to SessionManager, keepalive, deliver response."""
    user_id = str(update.effective_user.id)

    # Typing indicator while waiting
    stop_typing = asyncio.Event()
    typing_task = asyncio.create_task(
        _typing_keepalive(update, context, stop_typing)
    )

    _send_to_session_manager(text, source, user_id, media_path)

    try:
        raw = await _wait_for_response(subscriber, source)
    finally:
        stop_typing.set()
        typing_task.cancel()
        try:
            await typing_task
        except asyncio.CancelledError:
            pass

    clean = _strip_memory_tags(raw)
    if not clean:
        clean = "(no response)"

    for chunk in _split_message(clean):
        await update.effective_message.reply_text(chunk)

    # Cleanup downloaded media
    if media_path:
        try:
            os.unlink(media_path)
        except Exception:
            pass


# ── Message handlers ──────────────────────────────────────────────────────────

def _make_handlers(subscriber: ResponseSubscriber):

    async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_authorized(update):
            await update.message.reply_text("This bot is private.")
            return
        text = update.message.text
        log.info(f"Text from {update.effective_user.id}: {text[:60]}")
        await _handle_and_reply(update, context, subscriber, text)

    async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_authorized(update):
            await update.message.reply_text("This bot is private.")
            return
        voice = update.message.voice
        log.info(f"Voice ({voice.duration}s) from {update.effective_user.id}")

        if not config.get("VOICE_PROVIDER"):
            await update.message.reply_text(
                "Voice transcription is not configured (VOICE_PROVIDER not set)."
            )
            return

        await update.message.reply_chat_action("typing")
        try:
            tg_file = await voice.get_file()
            audio_bytes = await tg_file.download_as_bytearray()
            transcription = await _transcribe_voice(bytes(audio_bytes))
            if not transcription:
                await update.message.reply_text("Could not transcribe voice message.")
                return
            text = f"[Voice message transcribed]: {transcription}"
            log.info(f"Transcribed: {transcription[:80]}")
            await _handle_and_reply(update, context, subscriber, text)
        except Exception as e:
            log.error(f"Voice error: {e}")
            await update.message.reply_text("Could not process voice message.")

    async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_authorized(update):
            await update.message.reply_text("This bot is private.")
            return
        log.info(f"Photo from {update.effective_user.id}")
        await update.message.reply_chat_action("typing")
        try:
            photo = update.message.photo[-1]  # highest resolution
            tg_file = await photo.get_file()
            ts = int(time.time() * 1000)
            file_path = str(UPLOADS_DIR / f"image_{ts}.jpg")
            await tg_file.download_to_drive(file_path)
            caption = update.message.caption or "Analyze this image."
            text = f"[Image: {file_path}]\n\n{caption}"
            await _handle_and_reply(update, context, subscriber, text, media_path=file_path)
        except Exception as e:
            log.error(f"Photo error: {e}")
            await update.message.reply_text("Could not process image.")

    async def on_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not _is_authorized(update):
            await update.message.reply_text("This bot is private.")
            return
        doc = update.message.document
        log.info(f"Document ({doc.file_name}) from {update.effective_user.id}")
        await update.message.reply_chat_action("typing")
        try:
            tg_file = await doc.get_file()
            ts = int(time.time() * 1000)
            file_name = doc.file_name or f"file_{ts}"
            file_path = str(UPLOADS_DIR / f"{ts}_{file_name}")
            await tg_file.download_to_drive(file_path)
            caption = update.message.caption or f"Analyze: {doc.file_name}"
            text = f"[File: {file_path}]\n\n{caption}"
            await _handle_and_reply(update, context, subscriber, text, media_path=file_path)
        except Exception as e:
            log.error(f"Document error: {e}")
            await update.message.reply_text("Could not process document.")

    return on_text, on_voice, on_photo, on_document


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    token = config.get("TELEGRAM_BOT_TOKEN")
    if not token:
        log.error("TELEGRAM_BOT_TOKEN not set")
        sys.exit(1)

    # post_init runs inside run_polling()'s event loop — safe to get the loop here.
    async def post_init(application):
        loop = asyncio.get_event_loop()
        subscriber = ResponseSubscriber(loop)
        on_text, on_voice, on_photo, on_document = _make_handlers(subscriber)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
        application.add_handler(MessageHandler(filters.VOICE, on_voice))
        application.add_handler(MessageHandler(filters.PHOTO, on_photo))
        application.add_handler(MessageHandler(filters.Document.ALL, on_document))
        log.info(f"TelegramNode starting (authorized user: {AUTHORIZED_USER_ID or 'ANY'})")

    app = Application.builder().token(token).post_init(post_init).build()
    app.run_polling()


if __name__ == "__main__":
    main()
