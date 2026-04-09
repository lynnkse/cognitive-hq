# Relay v2 — Dev Log

## 2026-04-07 — Permission deadlock solved + concurrent_updates fix

### Problem
When a message came from Telegram (photo/text), tapping Allow/Deny on the inline keyboard did nothing. The same buttons worked when the message originated from CLI.

### Root cause
python-telegram-bot processes updates from the same chat **sequentially** by default. While `on_photo` (or any handler) was blocking on `await _wait_for_response(...)`, the callback query update (button tap) from the same chat was queued behind it. `on_photo` couldn't finish without permission; the callback couldn't run; classic deadlock.

CLI worked because no Telegram handler was blocking — callback ran freely.

### Fix
Added `concurrent_updates(True)` to the Application builder in `telegram_node.py`:
```python
app = Application.builder().token(token).concurrent_updates(True).post_init(post_init).build()
```

### Also built this session (from previous context)
- `permission_hook.py` — PermissionRequest hook that forwards to permission.sock, waits for decision, returns allow/deny JSON to Claude Code
- `claude_relay_wrapper.sh` — sets `CLAUDE_RELAY_SESSION=1` before exec'ing Claude; used as CLAUDE_PATH so relay's Claude process has the env var, distinguishing it from interactive sessions
- `.claude/settings.json` — registers PermissionRequest hook at project level
- `session_manager.py` — permission.sock server, `_handle_permission_conn`, `_resolve_permission`, `_publish_permission_request`
- `telegram_node.py` — `_permission_dispatcher` background task, `on_permission_callback`, inline Allow/Deny keyboard

### Known issue
`CLAUDE_RELAY_SESSION=1` leaks into interactive terminal sessions if started from the same shell as the relay. Need to ensure wrapper-set env var doesn't pollute interactive Claude Code sessions. Mitigation: use a separate terminal or `unset CLAUDE_RELAY_SESSION` before interactive use.

## 2026-04-08 — Telegram slash commands + permission hook fallback fix

### Slash commands implemented
Intercepted via python-telegram-bot `CommandHandler` before reaching Claude PTY.
All read local files directly — no Claude involvement, instant replies.

- `/help` — lists commands
- `/status` — relay health (SessionManager PID, session ID, sockets)
- `/usage` — 5h window + 7-day totals from session JSONL, timezone-aware reset times (USER_TIMEZONE), countdown ("in 2h 15m"), % display when USAGE_*_LIMIT set in .env
- `/model` — current Claude model from session JSONL
- `/clear` — deletes session ID file (fresh session on next restart)

**Bug found during /usage:** usage data is in `obj['message']['usage']`, not `obj['usage']`. Fixed.

**Usage limits:** set `USAGE_5H_LIMIT` and `USAGE_WEEK_LIMIT` in .env for percentage display. Limits are enforced server-side by Anthropic, not stored locally.

### Permission hook fallback fix
When `permission.sock` is unreachable (relay not running), hook now exits 1 so Claude Code falls through to its TUI instead of auto-denying all tool calls.

### Architecture clarification
This Claude (the interactive assistant) IS the relay's Claude — the same process receives messages from both Telegram and CLI. `CLAUDE_RELAY_SESSION=1` is correctly set; permission requests from tool use route through Telegram for approval.

## 2026-04-08 — Auto-allow safe permissions

Added `_auto_decision()` to `permission_hook.py`. Runs before connecting to `permission.sock`, so safe actions never reach Telegram.

**Auto-allowed:** Read/Glob/Grep, WebFetch/WebSearch, Edit/Write within `~` (except sensitive paths like ~/.ssh, ~/.aws), Bash commands without dangerous patterns.

**Always asks:** `sudo`, `rm -rf`, `git reset --hard`, `git push --force`, `dd`, `mkfs`, writes outside home dir or to sensitive paths, unknown tools.

**Kill switch:** `CLAUDE_AUTO_ALLOW=0` in environment disables all auto-allow.

**Bug fixed:** heredoc content containing dangerous-looking strings (e.g. "git reset --hard" in a log entry) was incorrectly triggering the ask-user path. Now only the first line (the actual shell command) is pattern-matched.

Logged to `/tmp/permission_hook.log` with `AUTO-ALLOW:` prefix for audit trail.

## 2026-04-08 — Fix missing final Telegram response after multi-tool runs

**Symptom:** After multiple permission approvals, CLI showed the summary but Telegram received nothing.

**Root cause:** `_RESPONSE_TIMEOUT` was 180s. Multi-tool runs with several 30-60s permission prompts exceeded this, causing the JSONL poller to time out and return a timeout message (or the actual response arrived after the poller had already given up).

**Fix 1:** Raised `_RESPONSE_TIMEOUT` to 600s (10 minutes).

**Fix 2:** Added `_STALL_FALLBACK` (30s): if the JSONL file stops growing but the last entry is not "text" type, return the best text we have rather than waiting for deadline. Handles edge case where Claude finishes without a closing text message.
