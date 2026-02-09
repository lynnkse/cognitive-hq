# Project Log — cognitive-hq

This file records human decisions, observations, hypotheses, and conclusions.
It is the authoritative source of project history and reasoning.

---

### 2026-02-03 — Repository Initialized

Created cognitive-hq repository as a template system for managing Claude context across stateless LLM sessions.

Key files:
- AGENT_RECREATION_GUIDE.md: Complete documentation for recreating .claude/ structure
- CLAUDE.md: Quick reference for Claude Code sessions
- .claude/: The context management directory structure

---

### 2026-02-04 — Phase 1 Planning Complete (Clawdbot Gateway)

**Goal:** Evaluate Clawdbot and design minimal Telegram gateway per MASTER_ROADMAP.md

**Key finding:** Clawdbot (now OpenClaw) already has everything we need:
- Telegram integration (production-ready via grammY)
- Cron/scheduling system with persistence
- Hooks for event-driven automation
- Skills system for extensibility
- Memory/embeddings (optional)

**Decision:** Use OpenClaw as-is. Configure, don't build.

**Artifacts produced:**
- `.claude/INTENT/CLAWDBOT_EVALUATION.md` - Full capability audit
- `.claude/INTENT/GATEWAY_DESIGN_V0.md` - Minimal gateway design

**OpenClaw cloned to:** `/home/lynnkse/openclaw`

**Next steps:**
1. Install OpenClaw globally
2. Create Telegram bot via @BotFather
3. Configure with cost-discipline settings (Haiku by default, no heartbeat)
4. Create workspace directories and system prompt
5. Test basic functionality

---

### 2026-02-06 — PIVOT: Custom Agent, Drop OpenClaw

**Decision:** Abandon OpenClaw/Clawdbot approach. Build custom always-on agent instead.

**Reason:** Better fit for our needs and budget. OpenClaw carries unnecessary complexity, dependencies (Node/grammY/SQLite-vec), and opinionated structure that doesn't align with what we actually need.

**New approach:** CloudCode Always-On Agent — a Python-based, modular skeleton:
- **Agent Runner** (always-on loop) — receives messages, calls CloudCode per-turn, executes tool calls
- **CloudCode Brain** (semi-stateless) — invoked on demand, returns structured JSON execution plans, never stays alive between turns
- **Telegram Emulator** — file/CLI-driven inbound, printed+logged outbound; swappable for real Telegram later
- **Memory Emulator** — JSONL-based long-term storage with simple API (put/search/get_latest); swappable for vector DB later

**Key design principles:**
- CloudCode is invoked per-turn ("ping-pong"), not long-running — tolerates session drops
- Agent runner is persistent, CloudCode is not
- All long-term memory is external (files/DB), never in context
- Modular: every component can be swapped independently (emulators → real services, local → GCP)
- Cost discipline: cheap models by default, expensive only on explicit request

**Architecture source:** `goals_and_architecture.txt` (root of repo)

**MVP success criteria:**
1. Start the runner
2. Send a message
3. Get a reply
4. Store + retrieve memory

**Previous OpenClaw artifacts now superseded:**
- `.claude/INTENT/CLAWDBOT_EVALUATION.md` — historical only
- `.claude/INTENT/GATEWAY_DESIGN_V0.md` — historical only
- `/home/lynnkse/openclaw` — no longer needed

---

### 2026-02-07 — MVP Implementation Complete (MVP-1 through MVP-7)

**All 7 MVP tasks implemented and tested. 90 tests passing.**

#### MVP-1: Repository Skeleton
- Created full folder structure: `src/`, `config/`, `state/`, `docs/`, `tests/`
- `pyproject.toml` (Python 3.10+, pydantic + pyyaml), `requirements.txt`, `.gitignore`
- All module stubs with docstrings, `__init__.py` files
- Config: `settings.example.yaml` + `settings.local.yaml` (gitignored)
- State dir with `.gitkeep` files; runtime state files gitignored
- CloudCode prompt pack: `system_context.md`, `tool_contract.md`, `output_format.md`, `examples.md`

#### MVP-2: Memory Emulator (14 tests)
- `src/adapters/memory_emulator.py` — `MemoryEmulator` class with JSONL backend
- API: `memory_put(text, tags, source, metadata)`, `memory_search(query, k)`, `memory_get_latest(n)`
- Naive case-insensitive multi-term text matching for search
- `src/runner/time_utils.py` — `utc_now()` helper (ISO 8601 UTC)

#### MVP-3: Telegram Emulator (16 tests)
- `src/adapters/telegram_emulator.py` — `TelegramEmulator` class
- Inbound: `enqueue_message()` appends to inbox JSONL
- Polling: `poll_inbox()` returns only unconsumed messages, advances offset
- Outbound: `send_message()` appends to outbox JSONL
- `src/cli/send_message.py` — CLI entry point: `python src/cli/send_message.py "hello"`

#### MVP-4: CloudCode Bridge (23 tests)
- `src/runner/plan_schema.py` — Pydantic models: `ToolName` enum, `ToolCall`, `ExecutionPlan`
- `src/runner/cloudcode_bridge.py` — `CloudCodeBridge` class
  - Loads and concatenates prompt pack files
  - Builds prompt from pack + runtime context (chat_id, state, transcript, user message)
  - Invokes `claude -p <prompt> --model <model> --no-input` via subprocess
  - Parses response JSON (handles markdown code fences), validates against schema
  - `CloudCodeError` for all failure modes

#### MVP-5: Tool Registry (10 tests)
- `src/adapters/tool_registry.py` — `ToolRegistry` class
- Maps 4 tool names to adapter methods, dispatches via `**kwargs`
- `execute()` for single calls, `execute_all()` for batches (continues past failures)

#### MVP-6: Agent Runner (14 tests)
- `src/runner/agent_runner.py` — `AgentRunner` class
  - `run()` — blocking polling loop with KeyboardInterrupt handling
  - `run_once()` — single-pass processing for testing/scripted use
  - Full cycle: poll inbox → invoke CloudCode → execute tools → apply state patch → log transcript
  - State persistence: `state/agent_state.json`
  - Session transcripts: `state/conversations/session_YYYYMMDD.jsonl`
  - CloudCode failures caught and logged, don't crash the loop
- `src/runner/logging_utils.py` — `setup_logging()`, `append_to_transcript()`
- `src/cli/run_agent.py` — CLI: `python src/cli/run_agent.py [--model haiku] [--poll-interval 2]`

#### MVP-7: End-to-End Tests (13 tests)
- `tests/test_e2e.py` — full integration tests (only CloudCode CLI call mocked)
- All success criteria verified:
  - Start runner, send message, get reply
  - Memory put / search / get_latest
  - Transcript logged with user/assistant/tool_results roles
  - Agent survives CloudCode failure and recovers
  - State persists across ticks and survives runner restart
  - Run loop starts/stops cleanly via threading

**Test suite: 90 tests, all passing (0.82s)**

**Next step:** Manual end-to-end testing with real CloudCode. Workflow:
1. Terminal 1: Claude Code session (for development/debugging)
2. Terminal 2: `python src/cli/run_agent.py` (agent running, waiting for messages)
3. Terminal 3: `python src/cli/send_message.py "hello"` (send messages, observe replies)

---

### 2026-02-08 — Socket IPC: Replace File-Based Messaging with Unix Domain Sockets

**Decision:** Replace the file-based cross-process communication (JSONL inbox) with Unix domain sockets.

**Reason:** The previous approach had `send_message.py` (process 2) appending to a shared JSONL file that `agent_runner.py` (process 1) read from. Two processes sharing a file without locking creates race condition risk as the system scales. Unix sockets provide a proper IPC channel — fast, no network overhead, same-machine only.

**Scope:** Only the inbound message path was changed (user → agent). Outbox stays file-based (single writer, no race condition). Memory stays in-process (only one caller).

**What was built:**
- `src/adapters/inbox_server.py` — Unix domain socket server (`InboxServer` class). Runs in a daemon thread inside the agent process. Listens on `state/agent.sock`. On each connection: reads JSON message, assigns `ts` + `message_id`, persists to inbox JSONL (audit trail, single writer), pushes to a thread-safe `queue.Queue`, sends back ack. Cleans up socket file on start/stop.
- `src/adapters/inbox_client.py` — Socket client (`send_to_agent()` function). Connects, sends newline-delimited JSON, reads ack, disconnects. Raises `AgentNotRunningError` if socket missing.
- `tests/test_inbox_server.py` (11 tests), `tests/test_inbox_client.py` (4 tests)

**What was refactored:**
- `TelegramEmulator` — inbox changed from file-based (read JSONL + offset tracking) to queue-based (drain `queue.Queue`). Constructor now takes `outbox_path` and optional `inbox_queue`. `enqueue_message()` puts directly into queue (for tests/in-process use). `poll_inbox()` drains queue non-blocking.
- `AgentRunner` — new optional `socket_path` param. When set, creates and manages `InboxServer` lifecycle (start before loop, stop in finally block). When None (in tests), no server — tests inject messages via `enqueue_message()`.
- `send_message.py` — now uses `send_to_agent()` socket client instead of creating a `TelegramEmulator` and writing files.
- `run_agent.py` — passes `socket_path=Path("state/agent.sock")` to runner.

**Protocol:** Newline-delimited JSON over Unix socket.
- Client sends: `{"type":"user_message","chat_id":"local-test","text":"hello"}\n`
- Server responds: `{"status":"ok","message_id":"...","ts":"..."}\n`
- One request-response per connection, then disconnect.

**Test suite:** 90 → 105 tests, all passing.

**Design rationale for keeping memory in-process:** Memory emulator is only called by the agent runner (same process). No cross-process boundary = no race condition. Sockets for memory would add complexity (separate server process, serialization overhead, lifecycle management) for zero benefit. Add a socket service for memory only when a second process needs access.

**Note for INTENT:** `CUSTOM_AGENT_V0.md` "Known Tradeoffs" item #2 states "File-based message queue (JSONL) has no locking. Fine for single-user local prototype. Must be replaced for production." This is now resolved — the inbox path uses sockets.

**Commit:** `6db9eb0 cleanup`

---

### 2026-02-08 — Documentation: Interactive Testing Guide + Telegram Swap Guide

**Created:**
- `docs/INTERACTIVE_TESTING_GUIDE.md` — Step-by-step guide for manually testing the agent, memory system, and Telegram emulator. Covers 2-terminal setup, where to observe results, Python REPL testing, 4-terminal real-time monitoring, troubleshooting, and verification checklist.
- `docs/TELEGRAM_SWAP_GUIDE.md` — Complete instructions for swapping the Telegram emulator for a real Telegram bot. Covers the interface contract, step-by-step implementation using `python-telegram-bot`, config changes, security notes (token safety, `allowed_chat_ids`), and rollback instructions.

---

### 2026-02-08 — Observation: Python Environment

The `.python-version` file points to `mrbsp3810` (Python 3.8.10), which is incompatible with the codebase (requires 3.10+ for `dict[str, Any]` syntax and Pydantic v2). Tests must be run with `~/.pyenv/versions/3.11.9/bin/python3 -m pytest tests/ -v`. Consider updating `.python-version` to a 3.11+ environment with deps installed.

---
