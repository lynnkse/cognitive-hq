# Derived Context Data — cognitive-hq

This file is NON-AUTHORITATIVE. See DERIVED_CONTEXT.md for rules.

---

## Repository Purpose (Updated 2026-02-14)

cognitive-hq serves three purposes:

1. **Meta-project**: Template system for managing Claude context across stateless LLM sessions
2. **Personal Command Center**: Telegram bot with persistent memory and semantic search
3. **Work Knowledge Base**: Accumulates domain knowledge across projects (robotics, SLAM, POMDP, etc.)

---

## Project Vision (from MASTER_ROADMAP.md)

Build a personal command center that supports:
- Research & engineering projects
- Business and monetization ideas
- Content creation pipelines
- Personal tracking (food, workouts, work hours)
- Secretary tasks (reminders, agenda, follow-ups)
- Communication aggregation
- Future automation and agent collaboration

---

## Key Design Decisions

### 1. LLM Context is NOT Memory (Non-negotiable)
- Context window = volatile RAM
- Files + databases = durable state
- All persistence must be explicit

### 2. Build Custom, Don't Use OpenClaw (Decision 2026-02-06)
- OpenClaw evaluated but dropped — too much complexity, wrong dependencies, opinionated structure
- Custom Python agent gives full control over architecture, cost, and modularity
- Every component is a swappable module (emulators -> real services)

### 3. CloudCode as "Brain" — Ping-Pong Architecture
- CloudCode is invoked per-turn, never long-running
- Agent runner is persistent, CloudCode is not
- This tolerates CloudCode session drops by design
- CloudCode reads context + prompt pack, returns structured JSON plan
- Agent runner executes the plan (tool calls, state updates, replies)

### 4. Cost Discipline
- Cheap models by default (Haiku)
- No background LLM loops
- Expensive models only on explicit request
- CloudCode invoked only when there's an inbound message to process

### 5. Modular Emulators -> Real Services
- Telegram emulator (queue/socket) -> real Telegram bot (guide written: `docs/TELEGRAM_SWAP_GUIDE.md`)
- Memory emulator (JSONL) -> vector DB
- Local runner -> Google Cloud VM

### 6. Unix Domain Sockets for IPC (Decision 2026-02-08)
- Cross-process messaging uses Unix domain sockets, not shared files
- Socket at `state/agent.sock` (exists while agent runs)
- Protocol: newline-delimited JSON, one request-response per connection
- InboxServer runs as daemon thread inside agent process, feeds a `queue.Queue`
- Inbox JSONL still written (by server, single-writer) for audit/persistence
- Memory stays in-process (no cross-process callers) — add socket only when needed

---

## Current Phase: Relay v2 Implementation (Architecture Complete)

**Status:** Relay v1 running. Relay v2 fully designed, implementation starting.

**This session runs through:** `claude-telegram-relay/tools/pipe_session.py` (PTY wrapper, PID chain: pipe_session.py → /dev/pts/8 → claude)

---

### Relay v2 Architecture

**Core insight:** SessionManagerNode owns the persistent Claude process. All frontends are clients that connect via sockets.

**Node graph:**
```
TelegramNode ──┐
CLINode ────────┤──► user_input.sock ──► SessionManagerNode ──► Claude (PTY)
ProactiveNode ─┘         ↑                      │
  ├── cron scheduler      │              claude_response.sock
  └── HTTP endpoint ──────┘                      │
       (Slack, email,                       RouterNode
        webhooks)                    ┌──────────┴──────────┐
                                Telegram              CLINode
                              (always for           display.sock
                               proactive)           (raw PTY bytes)
                                  │
                              MemoryNode (in-process)
                            ├── input enrichment (FACTS+GOALS+semantic)
                            └── output tag extraction ([REMEMBER]/[GOAL]/[DONE])
```

**Sockets:**
```
/tmp/cognitive-hq/
├── user_input.sock       NDJSON: {text, source, user_id, media_path?}
├── claude_response.sock  NDJSON: {text, source, user_id}  (ANSI-stripped)
└── display.sock          raw PTY bytes stream → CLINode stdout
```

**SessionManagerNode threads:**
1. PTY reader — reads master_fd, forwards raw to display.sock, detects sentinel
2. Queue processor — IDLE/GENERATING state machine, writes to master_fd
3. Socket listener — accepts user_input.sock connections, enqueues messages
4. Display server — holds CLINode display.sock connection

**Sentinel:** `<<RELAY_END_<uuid>>>` in system prompt. Marks end of every response. Missing sentinel = crash → restart with `--resume`.

**PTY:** `pty.openpty()` master/slave pair. Claude sees `/dev/pts/X` (real TTY). Required — Claude enters print mode with plain pipes.

**Session ID:** Find newest `.jsonl` in `~/.claude/projects/-home-lynnkse-cognitive-hq/` after spawn. Store in `~/.claude-relay/session_id`. Pass `--resume` on restart.

**Implementation order:**
1. ✅ `relay_v2/session_manager.py` + `relay_v2/cli_node.py` — DONE, verified 2026-04-03
2. `relay_v2/memory_node.py` — NEXT
3. `relay_v2/router_node.py` + `relay_v2/telegram_node.py`
4. `relay_v2/proactive_node.py`

**Open questions:** See LOG.md 2026-04-02, questions #1–14.

**MCPs:** None configured. Once Supabase MCP set up, Claude stores memories directly — tag system becomes fallback.

---

## Previous Phase: Fully Functional Telegram Bot with Memory & Voice

**Status:** Bot deployed with all core features operational. Persistent memory via Supabase, semantic search via pgvector, voice transcription via Groq.

**Architecture:** claude-telegram-relay (TypeScript/Bun) superseded Python agent.

**Bot command:** `~/.bun/bin/bun run src/relay.ts` (running in background, PID: 1898776)

**Features enabled:**
- ✅ Telegram integration (text messages)
- ✅ Claude Code session continuity (--resume)
- ✅ Persistent memory (Supabase PostgreSQL + pgvector)
- ✅ Semantic search (OpenAI embeddings via Edge Functions)
- ✅ Memory tags ([REMEMBER], [GOAL], [DONE])
- ✅ Voice message transcription (Groq Whisper API)
- ❌ Voice replies (TTS not configured)
- ❌ Phone calls (Telegram API does not support)
- ❌ Proactive check-ins (not configured)
- ❌ Always-on service (manual start required)

**Python agent status:** Superseded (code remains, 105 tests passing, but not in active use)

### Components (all implemented)

| Component | File(s) | Tests |
|-----------|---------|-------|
| Agent Runner | `src/runner/agent_runner.py` | 14 |
| CloudCode Bridge | `src/runner/cloudcode_bridge.py` | 13 |
| Plan Schema | `src/runner/plan_schema.py` | 10 |
| Telegram Emulator | `src/adapters/telegram_emulator.py` | 16 |
| Inbox Server (socket) | `src/adapters/inbox_server.py` | 11 |
| Inbox Client (socket) | `src/adapters/inbox_client.py` | 4 |
| Memory Emulator | `src/adapters/memory_emulator.py` | 14 |
| Tool Registry | `src/adapters/tool_registry.py` | 10 |
| Prompt Pack | `src/cloudcode_prompts/` | — |
| CLI: run_agent | `src/cli/run_agent.py` | — |
| CLI: send_message | `src/cli/send_message.py` | — |
| CLI: memory_cli | `src/cli/memory_cli.py` | Stub only |
| Logging | `src/runner/logging_utils.py` | — |
| Time Utils | `src/runner/time_utils.py` | — |
| E2E Tests | `tests/test_e2e.py` | 13 |

### Data Flow (One Cycle)

```
send_message.py  ---Unix socket--->  InboxServer (daemon thread)
                                          |
                                          v  (persist to inbox JSONL for audit)
                                          v  (push to queue.Queue)
                                          |
AgentRunner._tick()  <---poll_inbox()---  TelegramEmulator (drains queue)
     |
     v
CloudCodeBridge.invoke()  -->  claude -p <prompt> --model haiku --no-input
     |
     v  (parse JSON response into ExecutionPlan)
     |
ToolRegistry.execute_all(plan.tool_calls)
     |
     ├── telegram_send_message  -->  outbox JSONL
     ├── memory_put             -->  memory JSONL
     ├── memory_search          -->  in-memory scan
     └── memory_get_latest      -->  in-memory scan
     |
     v  (apply state_patch, log transcript)
     |
Loop waits for next message
```

### How to Run (2 terminals)

**Terminal 1 — Agent Runner** (always-on, waiting for messages):
```
python3 src/cli/run_agent.py
# Options: --model haiku --poll-interval 2 --timeout 30 --log-level INFO
```

**Terminal 2 — Send Messages** (via Unix socket):
```
python3 src/cli/send_message.py "hello agent"
python3 src/cli/send_message.py "remember that I prefer Python"
python3 src/cli/send_message.py "what do you know about me?"
```

### Observing Results
- Agent replies: `state/telegram_outbox.jsonl`
- Memory entries: `state/memory/memory_store.jsonl`
- Session transcript: `state/conversations/session_YYYYMMDD.jsonl`
- Agent state: `state/agent_state.json`
- Inbound audit log: `state/telegram_inbox.jsonl`

### CloudCode Output Schema
```json
{
  "assistant_message": "string",
  "tool_calls": [
    {"tool_name": "memory_put | memory_search | memory_get_latest | telegram_send_message", "args": {}}
  ],
  "state_patch": {},
  "notes": "optional, for logs only"
}
```

### Tool Schemas
- `telegram_send_message(chat_id, text)`
- `memory_put(text, tags, source, metadata)`
- `memory_search(query, k)`
- `memory_get_latest(n)`

---

## Resolved Questions

| Question | Answer |
|----------|--------|
| Python version? | 3.10+ required. Use `~/.pyenv/versions/3.11.9/bin/python3`. |
| How to invoke CloudCode? | `claude -p <prompt> --model <model> --no-input` via subprocess |
| Async or polling? | Simple polling loop (`time.sleep`) — good enough for MVP |
| CloudCode error handling? | `CloudCodeError` exception, caught in runner, logged in transcript, loop continues |
| Config format? | YAML — `config/settings.example.yaml` has all settings |
| Cross-process IPC? | Unix domain sockets at `state/agent.sock`. Newline-delimited JSON protocol. |
| File-based race conditions? | Solved. Inbox uses sockets. Outbox is single-writer. Memory is in-process. |

## Remaining Open Questions

1. Will `claude -p` with a very long prompt (prompt pack + transcript) work reliably?
2. Does the agent need to handle multi-turn tool calls (e.g., search memory then reply with results)?
3. Should `memory_cli.py` be fully implemented or is it low priority?

---

## Relay Architecture (Current Implementation)

### Data Flow
```
You → Telegram → Relay (Bun) → Claude Code CLI (--resume session_id) → Response
                                        ↓
                                  Supabase (pending setup)
                                  - messages table (conversation history)
                                  - memory table (facts, goals)
                                  - Embeddings via OpenAI (semantic search)
```

### Key Differences: Relay vs Python Agent

| Aspect | Python Agent (Superseded) | claude-telegram-relay (Current) |
|--------|--------------------------|--------------------------------|
| Context continuity | 20-message window (per-turn) | Session-based (--resume flag) |
| Memory | JSONL + naive text search | Supabase + semantic embeddings |
| Telegram | Emulator (files) | Real bot (grammY) |
| Language | Python | TypeScript/Bun |
| Output | Forced JSON schema | Natural text + memory tags |
| Voice | Not supported | Groq/Whisper supported |

### Memory Tag System

Claude auto-detects facts/goals in responses and tags them:
- `[REMEMBER: fact]` → saved to Supabase memory table
- `[GOAL: text | DEADLINE: date]` → tracked with deadline
- `[DONE: search text]` → marks goal complete

Tags are stripped before showing to user (invisible automation).

**Current limitation:** Tags generated but not persisted (needs Supabase setup).

### Key Files (Relay)

| File | Purpose |
|------|---------|
| `claude-telegram-relay/src/relay.ts` | Core bot (Telegram ↔ Claude CLI bridge) |
| `claude-telegram-relay/src/memory.ts` | Memory tag processing + context retrieval |
| `claude-telegram-relay/.env` | Bot configuration (gitignored) |
| `claude-telegram-relay/db/schema.sql` | Database schema (for Supabase) |
| `claude-telegram-relay/CLAUDE.md` | Setup guide (7 phases) |

### Key Files (Python Agent - Legacy)

| File | Purpose | Status |
|------|---------|--------|
| `src/cli/run_agent.py` | Start the agent | Superseded |
| `src/runner/agent_runner.py` | Always-on polling loop | Superseded |
| `src/runner/cloudcode_bridge.py` | Invokes Claude CLI, parses JSON plans | Superseded |
| `.claude/INTENT/CUSTOM_AGENT_V0.md` | Design intent for Python agent | Historical |
| `docs/INTERACTIVE_TESTING_GUIDE.md` | Testing guide for Python agent | Historical |

---

## User Context & Usage Patterns (Added 2026-02-14)

### User Profile
- **Name:** Lynn
- **Timezone:** Asia/Jerusalem
- **Work:** Autonomous robot navigation, SLAM, POMDP
- **Use case:** Personal command center + work knowledge base

### System Usage Strategy

**Unified Knowledge Base Approach:**
- Single Supabase database for work + personal knowledge
- Organization via `channel` field and `metadata` JSON
- Semantic search across all domains
- Memory tags to capture key facts/goals

**Database Organization:**
```
messages table:
├── Personal conversations (channel: "personal")
├── Work discussions (channel: "work", metadata: {"project": "robot-nav"})
└── General queries (channel: "telegram")

memory table:
├── Personal facts (metadata: {"type": "personal"})
├── Work facts (metadata: {"type": "work", "domain": "robotics"})
└── Goals with deadlines (type: "goal")
```

**Work Knowledge Domains:**
- SLAM (Simultaneous Localization and Mapping)
- POMDP (Partially Observable Markov Decision Process)
- Robot navigation algorithms
- Sensor systems (e.g., Velodyne VLP-16 LiDAR)
- Particle filters, FastSLAM

**Recommended Memory Tag Usage:**
```
[REMEMBER: Using FastSLAM2.0 with particle filter, 500 particles]
[REMEMBER: Sensor: Velodyne VLP-16 LiDAR, 16 channels, 100m range]
[GOAL: Implement loop closure detection | DEADLINE: 2026-03-01]
[REMEMBER: POMDP solver: POMCP with 10,000 particles]
```

### Voice Input Patterns

**Primary:** Telegram voice messages (Groq Whisper transcription)
- Send voice → auto-transcribed → processed by Claude
- Conversation saved to Supabase with semantic embeddings
- Retrieval via meaning, not keywords

**Secondary:** OS-level dictation for Claude Code terminal
- Linux: `gnome-dictation` (install if needed)
- Quick dictation for commands/queries

### Model Selection

**Current:** Claude Sonnet 4.5 (default)
- Balances quality and cost
- Good for technical discussions (SLAM, POMDP)
- Usage tracked at claude.ai/account

**Future:** Could switch to Haiku for simple queries if cost becomes concern
- Modify relay.ts to add `--model haiku` for specific patterns
- Keep Sonnet for complex technical discussions

### Best Practices for This System

1. **Use liberal [REMEMBER] tags** for important facts/decisions
2. **Tag work vs personal** in conversation ("Let's discuss my robot project...")
3. **Use voice for convenience** (hands-free during lab work)
4. **Query accumulated knowledge regularly:**
   - "What SLAM approach am I using?"
   - "Show me all sensor decisions"
   - "Summarize my POMDP implementation"
5. **Set goals with deadlines** for project tracking
6. **Trust semantic search** - describe what you need, don't keyword hunt

### System Limitations & Workarounds

**Limitation:** Claude Code CLI has no native voice input
**Workaround:** Use Telegram bot for voice → Claude Code session for complex work

**Limitation:** No phone call support (Telegram API restriction)
**Workaround:** Voice messages work perfectly

**Limitation:** Bot requires manual start (not always-on yet)
**Workaround:** Can set up as systemd service (Phase 5 in CLAUDE.md)

**Limitation:** Cross-context search requires same database
**Workaround:** Using channel tags to organize while keeping searchability
