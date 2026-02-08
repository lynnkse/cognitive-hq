"""Tests for the Telegram emulator adapter."""

import json
from pathlib import Path

import pytest

from src.adapters.telegram_emulator import TelegramEmulator


@pytest.fixture
def tg(tmp_path):
    """Create a TelegramEmulator backed by temp files."""
    return TelegramEmulator(
        inbox_path=tmp_path / "inbox.jsonl",
        outbox_path=tmp_path / "outbox.jsonl",
    )


class TestEnqueueMessage:
    def test_creates_record_with_required_fields(self, tg):
        rec = tg.enqueue_message("hello")
        assert rec["text"] == "hello"
        assert rec["type"] == "user_message"
        assert rec["chat_id"] == "local-test"
        assert "ts" in rec
        assert "message_id" in rec

    def test_custom_chat_id(self, tg):
        rec = tg.enqueue_message("hi", chat_id="my-chat")
        assert rec["chat_id"] == "my-chat"

    def test_appends_to_inbox_file(self, tg):
        tg.enqueue_message("first")
        tg.enqueue_message("second")
        lines = tg.inbox_path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert json.loads(lines[0])["text"] == "first"
        assert json.loads(lines[1])["text"] == "second"

    def test_unique_message_ids(self, tg):
        r1 = tg.enqueue_message("a")
        r2 = tg.enqueue_message("b")
        assert r1["message_id"] != r2["message_id"]


class TestPollInbox:
    def test_empty_inbox(self, tg):
        assert tg.poll_inbox() == []

    def test_returns_new_messages(self, tg):
        tg.enqueue_message("hello")
        msgs = tg.poll_inbox()
        assert len(msgs) == 1
        assert msgs[0]["text"] == "hello"

    def test_advances_offset(self, tg):
        tg.enqueue_message("first")
        tg.poll_inbox()
        # Second poll should return nothing
        assert tg.poll_inbox() == []

    def test_returns_only_new_after_offset(self, tg):
        tg.enqueue_message("first")
        tg.poll_inbox()
        tg.enqueue_message("second")
        msgs = tg.poll_inbox()
        assert len(msgs) == 1
        assert msgs[0]["text"] == "second"

    def test_multiple_new_messages(self, tg):
        tg.enqueue_message("a")
        tg.enqueue_message("b")
        tg.enqueue_message("c")
        msgs = tg.poll_inbox()
        assert len(msgs) == 3
        assert [m["text"] for m in msgs] == ["a", "b", "c"]


class TestSendMessage:
    def test_creates_outbox_record(self, tg):
        rec = tg.send_message(chat_id="local-test", text="hi there")
        assert rec["type"] == "agent_message"
        assert rec["chat_id"] == "local-test"
        assert rec["text"] == "hi there"
        assert "ts" in rec

    def test_in_reply_to(self, tg):
        rec = tg.send_message(
            chat_id="local-test", text="reply", in_reply_to="msg-123"
        )
        assert rec["in_reply_to"] == "msg-123"

    def test_in_reply_to_default_empty(self, tg):
        rec = tg.send_message(chat_id="local-test", text="hi")
        assert rec["in_reply_to"] == ""

    def test_appends_to_outbox_file(self, tg):
        tg.send_message(chat_id="c1", text="first")
        tg.send_message(chat_id="c1", text="second")
        lines = tg.outbox_path.read_text().strip().split("\n")
        assert len(lines) == 2


class TestGetOutbox:
    def test_empty_outbox(self, tg):
        assert tg.get_outbox() == []

    def test_returns_all_outbox_messages(self, tg):
        tg.send_message(chat_id="c1", text="a")
        tg.send_message(chat_id="c1", text="b")
        msgs = tg.get_outbox()
        assert len(msgs) == 2
        assert msgs[0]["text"] == "a"
        assert msgs[1]["text"] == "b"


class TestRoundTrip:
    def test_enqueue_poll_reply_cycle(self, tg):
        """Simulate a full user->agent cycle."""
        # User sends a message
        user_msg = tg.enqueue_message("hello agent")
        # Agent runner polls
        new_msgs = tg.poll_inbox()
        assert len(new_msgs) == 1
        # Agent replies
        reply = tg.send_message(
            chat_id=new_msgs[0]["chat_id"],
            text="hello user!",
            in_reply_to=new_msgs[0]["message_id"],
        )
        # Verify outbox
        outbox = tg.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["in_reply_to"] == user_msg["message_id"]
