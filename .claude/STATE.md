# STATE — Git Commits

<!-- This file is auto-populated with git commits -->

---

## Current State (2026-02-08)

**Branch:** master
**Commits:**
- `6db9eb0` — Socket IPC + docs (2026-02-08)
- `0180cec` — MVP-7
- `0030c36` — Initial commit

**Uncommitted:** `.claude/` context files (STATE.md, LOG.md, TODO.md, DERIVED_CONTEXT.DATA.md, TREE.txt)

**Active direction:** Custom always-on agent (Python) — MVP + Socket IPC complete, awaiting manual testing

**Test suite:** 105 tests, all passing (Python 3.11.9)

**Test command:** `~/.pyenv/versions/3.11.9/bin/python3 -m pytest tests/ -v`
(The `.python-version` file points to `mrbsp3810` which is Python 3.8 and lacks deps. Use 3.11.9 explicitly.)

---

## File Structure Changes

### 2026-02-08 — Socket IPC: Replace File-Based IPC with Unix Domain Sockets

Replaced cross-process file-based inbox communication with Unix domain sockets.
Inbound messages now flow: `send_message.py` → Unix socket → `InboxServer` (thread) → `Queue` → `AgentRunner`.
Outbox stays file-based (single writer, no race condition). Memory stays in-process.

**New files:**
```
src/adapters/
├── inbox_server.py    — Unix socket server (daemon thread, feeds queue)
├── inbox_client.py    — Socket client (send_to_agent() function)

tests/
├── test_inbox_server.py  (11 tests)
├── test_inbox_client.py  (4 tests)

docs/
├── INTERACTIVE_TESTING_GUIDE.md  — How to test agent, memory, emulator interactively
├── TELEGRAM_SWAP_GUIDE.md        — How to swap emulator for real Telegram bot
```

**Modified files:**
- `src/adapters/telegram_emulator.py` — inbox switched from file+offset to `queue.Queue`
- `src/runner/agent_runner.py` — added `socket_path` param, starts/stops `InboxServer`
- `src/cli/send_message.py` — uses socket client instead of file append
- `src/cli/run_agent.py` — passes `socket_path=state/agent.sock` to runner
- `config/settings.example.yaml` — added `socket_path` setting
- `.gitignore` — added `state/agent.sock`
- All test fixtures updated (removed `inbox_path` param)

**Test suite:** 90 → 105 tests (15 new socket transport tests)

---

### 2026-02-07 — MVP Implementation Complete

Full agent skeleton implemented:
```
src/
├── runner/
│   ├── agent_runner.py      — always-on loop, orchestrates everything
│   ├── cloudcode_bridge.py  — invokes Claude CLI, parses JSON plans
│   ├── plan_schema.py       — Pydantic models (ExecutionPlan, ToolCall, ToolName)
│   ├── logging_utils.py     — setup_logging(), append_to_transcript()
│   └── time_utils.py        — utc_now() ISO 8601
├── adapters/
│   ├── telegram_emulator.py — queue-based inbox, file-based outbox
│   ├── inbox_server.py      — Unix socket server for cross-process inbound
│   ├── inbox_client.py      — Unix socket client for send_message.py
│   ├── memory_emulator.py   — JSONL long-term storage (put/search/get_latest)
│   └── tool_registry.py     — dispatches tool calls to adapters
├── cloudcode_prompts/
│   ├── system_context.md
│   ├── tool_contract.md
│   ├── output_format.md
│   └── examples.md
└── cli/
    ├── run_agent.py          — entry point: start the agent
    ├── send_message.py       — CLI: send message via Unix socket
    └── memory_cli.py         — CLI: interact with memory (stub)

tests/
├── test_memory_emulator.py   (14 tests)
├── test_telegram_emulator.py (16 tests)
├── test_plan_schema.py       (10 tests)
├── test_cloudcode_bridge.py  (13 tests)
├── test_tool_registry.py     (10 tests)
├── test_agent_runner.py      (14 tests)
├── test_e2e.py               (13 tests)
├── test_inbox_server.py      (11 tests)
└── test_inbox_client.py      (4 tests)

config/
├── settings.example.yaml
└── settings.local.yaml (gitignored)

state/  (runtime data, gitignored except .gitkeep)
├── agent.sock (Unix socket, exists while agent runs)
├── agent_state.json
├── telegram_inbox.jsonl (audit log, written by InboxServer)
├── telegram_outbox.jsonl
├── conversations/session_YYYYMMDD.jsonl
└── memory/memory_store.jsonl
```

---

### 2026-02-04 — Initial .claude/ setup

Created complete .claude/ directory structure:
```
.claude/
├── ABSTRACTIONS.md
├── BOOTSTRAP.md
├── DERIVED_CONTEXT.DATA.md
├── DERIVED_CONTEXT.md
├── INTENT/
│   ├── CLAWDBOT_EVALUATION.md   (NEW - OpenClaw audit)
│   ├── GATEWAY_DESIGN_V0.md     (NEW - Gateway design)
│   ├── MASTER_ROADMAP.md        (existing)
│   ├── README.md
│   └── REFERENCES/
├── LOG.md
├── log.sh
├── ONBOARDING.md
├── RULES.md
├── settings.local.json
├── STATE.md
├── TODO.md
├── tree.sh
├── TREE.txt
└── WORKFLOW.md
```

Also created:
- `/home/lynnkse/cognitive-hq/CLAUDE.md` - Quick reference for Claude Code
