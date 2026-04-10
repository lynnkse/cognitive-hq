"""
SupabaseClient — Fire-and-forget persistence layer for relay v2.

Saves messages and memory entries to Supabase via REST API.
All writes run in a background thread so the relay is never blocked.

Memory tags parsed from Claude responses:
  [REMEMBER: fact]
  [GOAL: goal text | DEADLINE: optional date]
  [DONE: search text for completed goal]

These tags are stripped from the response text before it reaches Telegram.
"""

import json
import logging
import re
import threading
import urllib.request
import urllib.error
from typing import Optional

import config

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Tag patterns
# ------------------------------------------------------------------

_REMEMBER_RE = re.compile(r'\[REMEMBER:\s*(.+?)\]', re.DOTALL)
_GOAL_RE = re.compile(r'\[GOAL:\s*(.+?)(?:\s*\|\s*DEADLINE:\s*(.+?))?\]', re.DOTALL)
_DONE_RE = re.compile(r'\[DONE:\s*(.+?)\]', re.DOTALL)
_ALL_TAGS_RE = re.compile(r'\[(REMEMBER|GOAL|DONE):[^\]]+\]', re.DOTALL)


# ------------------------------------------------------------------
# HTTP helpers
# ------------------------------------------------------------------

def _rest_insert(table: str, payload: dict) -> bool:
    """Insert one row into a Supabase table via REST API. Returns True on success."""
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        return False
    url = f"{config.SUPABASE_URL.rstrip('/')}/rest/v1/{table}"
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "apikey": config.SUPABASE_ANON_KEY,
            "Authorization": f"Bearer {config.SUPABASE_ANON_KEY}",
            "Content-Type": "application/json",
            "Prefer": "return=minimal",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 201, 204)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")
        log.warning(f"Supabase insert {table} failed {e.code}: {body[:200]}")
        return False
    except Exception as e:
        log.warning(f"Supabase insert {table} error: {e}")
        return False


def _fire(fn, *args):
    """Run fn(*args) in a daemon thread — non-blocking."""
    threading.Thread(target=fn, args=args, daemon=True).start()


# ------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------

def save_message(role: str, content: str, channel: str = "telegram", metadata: Optional[dict] = None):
    """Save a message to the messages table (non-blocking)."""
    payload = {
        "role": role,
        "content": content,
        "channel": channel,
        "metadata": metadata or {},
    }
    _fire(_rest_insert, "messages", payload)


def save_memory(type_: str, content: str, deadline: Optional[str] = None, priority: int = 0):
    """Save a memory entry (fact, goal, preference, completed_goal) — non-blocking."""
    payload: dict = {
        "type": type_,
        "content": content.strip(),
        "priority": priority,
        "metadata": {},
    }
    if deadline:
        payload["deadline"] = deadline.strip()
    _fire(_rest_insert, "memory", payload)


def process_response(text: str, channel: str = "telegram") -> str:
    """
    Parse memory tags from Claude's response text, save them to Supabase,
    and return the cleaned text (tags stripped) for delivery to the user.
    """
    facts = _REMEMBER_RE.findall(text)
    goals = _GOAL_RE.findall(text)
    dones = _DONE_RE.findall(text)

    for fact in facts:
        fact = fact.strip()
        if fact:
            log.info(f"Memory: saving fact: {fact[:60]}")
            save_memory("fact", fact)

    for goal_text, deadline in goals:
        goal_text = goal_text.strip()
        deadline = deadline.strip() if deadline else None
        if goal_text:
            log.info(f"Memory: saving goal: {goal_text[:60]}")
            save_memory("goal", goal_text, deadline=deadline)

    for done_text in dones:
        done_text = done_text.strip()
        if done_text:
            log.info(f"Memory: goal completed: {done_text[:60]}")
            save_memory("completed_goal", f"Completed: {done_text}")

    # Strip all tags from delivered text
    cleaned = _ALL_TAGS_RE.sub("", text).strip()
    return cleaned
