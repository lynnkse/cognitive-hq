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

---

## Current State (2026-04-02)

**Branch:** master

**Active direction:** Relay v2 — Phase 1 complete, Phase 2 (MemoryNode) next.

**Relay v1 status:** Running in background. Still the active bot.

**Relay v2 status:** Phase 1 working and verified (LOG.md 2026-04-03).
- `relay_v2/session_manager.py` + `relay_v2/cli_node.py` + `relay_v2/config.py` committed
- CLINode proxy confirmed transparent — identical UX to direct `claude`
- Next: `relay_v2/memory_node.py` — input enrichment + Supabase tag extraction

**First implementation target:** `claude-telegram-relay/relay_v2/session_manager.py` + `cli_node.py`

---

## Current State (2026-02-14)

**Branch:** master

**Uncommitted:**
- `claude-telegram-relay/` — New directory (cloned from github.com/godagoo/claude-telegram-relay)
- `claude-telegram-relay/.env` — Bot configuration (gitignored)
- `claude-telegram-relay/src/relay.ts` — Modified (CLAUDECODE env var fix)

**Active direction:** Telegram bot via claude-telegram-relay (TypeScript/Bun) — supersedes Python agent

**Bot status:** Running in background (PID 2402874, `~/.bun/bin/bun src/relay.ts`)

**Features enabled:**
- ✅ Telegram integration (bot token configured)
- ✅ Claude Code session continuity (per-user persistent sessions - WORKING!)
- ✅ Persistent memory (Supabase + pgvector)
- ✅ Semantic search (OpenAI embeddings)
- ✅ Memory tags ([REMEMBER], [GOAL], [DONE])
- ✅ Voice message transcription (Groq Whisper configured, untested)

- **See LOG.md 2026-02-15** for full debugging session details

**Test command:** Send message or voice message to Telegram bot (@lynnkse's bot)

---

### 2026-02-14 — claude-telegram-relay Deployment

Switched from custom Python agent to existing TypeScript relay for better context continuity.

**New directory structure:**
```
claude-telegram-relay/
├── src/
│   ├── relay.ts           — Core relay (modified: CLAUDECODE env var)
│   ├── memory.ts          — Memory tag processing ([REMEMBER], [GOAL], [DONE])
│   └── transcribe.ts      — Voice transcription (not configured)
├── config/
│   └── profile.example.md — User profile template
├── db/
│   └── schema.sql         — Supabase database schema
├── supabase/
│   └── functions/
│       ├── embed/         — Auto-embedding Edge Function
│       └── search/        — Semantic search Edge Function
├── .env                   — Bot configuration (gitignored)
├── package.json           — Bun dependencies
└── node_modules/          — Installed via `bun install`
```

**Modified files:**
- `src/relay.ts` line 207: Added `CLAUDECODE: undefined` to allow nested sessions

**Configuration (.env):**
- Telegram bot token: configured (revoked old, using new)
- User ID: 310065542
- User name: Lynn
- Timezone: Asia/Jerusalem
- Claude path: /home/lynnkse/.npm-global/bin/claude
- Project dir: /home/lynnkse/cognitive-hq
- Supabase URL: https://jcwdfuusolpxnciqgstl.supabase.co
- Supabase anon key: configured
- Voice provider: groq (Groq Whisper API)
- Groq API key: configured

**Runtime:**
- Bot process: `~/.bun/bin/bun run src/relay.ts` (background)
- Lock file: `~/.claude-relay/bot.lock`
- Session tracking: `~/.claude-relay/session.json`

**Python agent status:** Stopped (superseded by relay)
