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

### 2026-02-14 — PIVOT: Switch to claude-telegram-relay (Supersedes Python Agent)

**Decision:** Adopt existing claude-telegram-relay (TypeScript/Bun) instead of continuing with custom Python agent.

**Reason:**
- Python agent was per-turn invocation (20-message context window) — user wanted long-running sessions with deep context
- claude-telegram-relay already implements `--resume` flag for session continuity
- Built-in semantic memory via Supabase + embeddings
- Real Telegram bot (grammY), not emulator
- Voice transcription support (Groq/Whisper)
- Production-ready daemon support (launchd/systemd/PM2)
- Would take weeks to build all these features in Python version

**What was built:**
- Installed Bun runtime v1.3.9 (`~/.bun/bin/bun`)
- Cloned claude-telegram-relay to `/home/lynnkse/cognitive-hq/claude-telegram-relay`
- Configured `.env`:
  - `TELEGRAM_BOT_TOKEN`: 8403736964:AAH5u-FvHan-xELGDL3glu9B7NjEGtdnmCw (revoked old token)
  - `TELEGRAM_USER_ID`: 310065542
  - `USER_NAME`: Lynn
  - `USER_TIMEZONE`: Asia/Jerusalem
  - `CLAUDE_PATH`: /home/lynnkse/.npm-global/bin/claude
  - `PROJECT_DIR`: /home/lynnkse/cognitive-hq
  - Supabase vars commented out (not configured yet)
- Modified `src/relay.ts` line 207: Set `CLAUDECODE: undefined` to allow nested Claude sessions
- Successfully deployed bot — running in background (PID: 1746159)
- Bot tested and confirmed working on Telegram

**Current status:**
- ✅ Bot receives Telegram messages
- ✅ Calls Claude Code CLI with context
- ✅ Returns responses to Telegram
- ✅ Session continuity via `--resume` flag (within-session memory works)
- ❌ No cross-session memory (requires Supabase setup)
- ❌ No semantic search (requires Supabase + OpenAI embeddings)

**Architecture:**
```
You → Telegram → Relay (Bun) → Claude Code (--resume session_id) → Response
                                        ↓
                                  Supabase (pending setup)
```

**Previous Python agent artifacts now superseded:**
- `src/` — Python agent code (MVP-1 through MVP-7)
- `tests/` — 105 passing tests for Python agent
- `docs/INTERACTIVE_TESTING_GUIDE.md` — Python-specific
- Python virtual env `cognitive-hq` (still exists, not needed for relay)

**Next step:** Configure Supabase for persistent memory (facts, goals, semantic search).

---

### 2026-02-14 — Supabase Configuration Complete: Semantic Memory Live

**Decision:** Configure Supabase for persistent memory and semantic search via OpenAI embeddings.

**Setup completed:**

**1. Supabase Project Created**
- Project name: lynnkse's Project
- Project URL: `https://jcwdfuusolpxnciqgstl.supabase.co`
- Region: Central EU (Frankfurt)
- Anon key configured in `.env`

**2. Database Schema Deployed**
- Ran `db/schema.sql` via Supabase SQL Editor
- Created tables:
  - `messages` — conversation history (id, created_at, role, content, channel, metadata, embedding VECTOR(1536))
  - `memory` — facts & goals (id, created_at, type, content, deadline, completed_at, priority, metadata, embedding VECTOR(1536))
  - `logs` — observability (id, created_at, level, event, message, session_id, duration_ms)
- Created indexes for performance (created_at DESC, type, level)
- Enabled Row Level Security with policies for service role
- Created helper functions:
  - `get_recent_messages(limit_count)` — retrieve recent conversation
  - `get_active_goals()` — retrieve active goals with deadlines
  - `get_facts()` — retrieve all stored facts
  - `match_messages(query_embedding, threshold, count)` — semantic search messages
  - `match_memory(query_embedding, threshold, count)` — semantic search memory
- Enabled pgvector extension for embedding similarity search

**3. OpenAI API Key Configured**
- Stored OpenAI API key in Supabase Edge Function secrets (not in .env for security)
- Secret name: `OPENAI_API_KEY`
- Used for generating text embeddings via `text-embedding-3-small` model
- Cost: ~$0.0001 per message (very cheap)

**4. Edge Functions Deployed**
- **embed** function — Auto-generates embeddings on INSERT
  - Triggered via database webhooks
  - Calls OpenAI embeddings API
  - Updates row with 1536-dimension vector
  - Handles both messages and memory tables
- **search** function — Semantic search endpoint
  - Accepts query text
  - Generates query embedding
  - Calls `match_messages()` or `match_memory()` RPC
  - Returns similar entries ranked by cosine similarity

**5. Database Webhooks Configured**
- **embed_messages** webhook:
  - Table: `public.messages`
  - Event: INSERT
  - Action: Call `embed` Edge Function
  - Auto-generates embeddings for new messages
- **embed_memory** webhook:
  - Table: `public.memory`
  - Event: INSERT
  - Action: Call `embed` Edge Function
  - Auto-generates embeddings for new facts/goals

**6. Bot Configuration Updated**
- Updated `claude-telegram-relay/.env`:
  - `SUPABASE_URL=https://jcwdfuusolpxnciqgstl.supabase.co`
  - `SUPABASE_ANON_KEY=sb_publishable_B63IA6zBnJmSFRhmGnbUHA_ZMKouMlN`
- Restarted bot with Supabase enabled

**Architecture (Final):**
```
You → Telegram → Relay (Bun) → Claude Code (--resume session_id) → Response
                 ↓                          ↓
            saveMessage()            [REMEMBER] tags detected
                 ↓                          ↓
            Supabase                  processMemoryIntents()
                 ↓                          ↓
         INSERT into messages      INSERT into memory
                 ↓                          ↓
         Webhook triggers          Webhook triggers
                 ↓                          ↓
         embed() Edge Function     embed() Edge Function
                 ↓                          ↓
         OpenAI embeddings API     OpenAI embeddings API
                 ↓                          ↓
         UPDATE with vector        UPDATE with vector
                 ↓                          ↓
         Semantic search ready     Semantic search ready
```

**Tested and verified:**
- ✅ Messages saved to database with auto-embedding
- ✅ Facts stored via `[REMEMBER]` tags
- ✅ Semantic search retrieves related content by meaning
- ✅ Memory persists across sessions (survives bot restart)
- ✅ Bot can answer "what did I eat?" and find "I had sushi"

**Current status:**
- ✅ Telegram bot live and receiving messages
- ✅ Claude Code integration with session continuity
- ✅ Persistent memory (Supabase)
- ✅ Semantic search (OpenAI embeddings)
- ✅ Auto-embedding on new messages/facts
- ✅ Memory tag system ([REMEMBER], [GOAL], [DONE])
- ❌ Voice transcription (not configured)
- ❌ Proactive check-ins (not configured)
- ❌ Always-on service (manual start required)

**Files modified:**
- `claude-telegram-relay/.env` — Added Supabase credentials

**Supabase resources:**
- Database: 3 tables, 8 functions, 2 webhooks
- Edge Functions: 2 deployed (embed, search)
- Secrets: 1 configured (OPENAI_API_KEY)

**Next steps:** Voice transcription setup (Groq or local Whisper).

---

### 2026-02-14 — Voice Transcription Enabled: Groq Integration Complete

**Decision:** Enable voice message support using Groq's free cloud API instead of local Whisper.

**Rationale:**
- Groq offers state-of-the-art Whisper model (whisper-large-v3-turbo)
- Free tier: 2,000 transcriptions per day (no credit card)
- Sub-second transcription speed
- No local setup required (no ffmpeg, no model downloads)
- Internet connection required, but acceptable tradeoff

**Implementation:**
1. **Groq API Key Obtained**
   - Created account at console.groq.com
   - Generated API key (stored securely in .env)
   - Stored in `claude-telegram-relay/.env`

2. **Environment Configuration**
   - Added to `.env`:
     - `VOICE_PROVIDER=groq`
     - `GROQ_API_KEY=<redacted>`
   - Installed missing dependency: `dotenv@17.3.1`

3. **Voice Handling Already Implemented**
   - Bot already has full voice message handling in `relay.ts:267-313`
   - Flow: Voice message → Download from Telegram → Buffer → `transcribe()` → Text
   - Transcription module routes to Groq or local based on `VOICE_PROVIDER`
   - Transcribed text saved to Supabase with `[Voice Xs]` prefix
   - Response generated using same Claude Code session continuity

4. **Testing**
   - Ran `bun setup/test-voice.ts`
   - ✅ Groq API key validated
   - ✅ Model `whisper-large-v3-turbo` available
   - ✅ Voice transcription ready

5. **Bot Restarted**
   - Stopped previous instance (PID: 1746159)
   - Started with voice support enabled (PID: 1898776)
   - Running in background, logs to `/tmp/relay.log`

**Voice Message Flow:**
```
Telegram voice message → bot.on("message:voice")
         ↓
Download voice file from Telegram API
         ↓
transcribe(buffer) → Groq Whisper API
         ↓
"[Voice 5s]: Hello, what's the weather today?"
         ↓
saveMessage(user, transcription)
         ↓
getRelevantContext() + getMemoryContext()
         ↓
callClaude(enriched_prompt, {resume: true})
         ↓
processMemoryIntents() → extract [REMEMBER] tags
         ↓
saveMessage(assistant, response)
         ↓
sendResponse() → Telegram
```

**Voice Call Capability:**
- Telegram bots **cannot receive phone calls** (Telegram API limitation)
- Voice messages: ✅ Fully supported (send voice → bot transcribes → responds with text)
- Voice replies: ❌ Not implemented (would need ElevenLabs TTS integration)
- Alternative: User can use Telegram's native voice-to-text before sending

**Current Full Status:**
- ✅ Telegram bot live and receiving messages
- ✅ Claude Code integration with session continuity
- ✅ Persistent memory (Supabase + pgvector)
- ✅ Semantic search (OpenAI embeddings)
- ✅ Auto-embedding on new messages/facts
- ✅ Memory tag system ([REMEMBER], [GOAL], [DONE])
- ✅ **Voice message transcription (Groq Whisper)**
- ❌ Voice replies (TTS not configured)
- ❌ Phone calls (not supported by Telegram bot API)
- ❌ Proactive check-ins (not configured)
- ❌ Always-on service (manual start required)

**Files modified:**
- `claude-telegram-relay/.env` — Added VOICE_PROVIDER=groq, GROQ_API_KEY
- `claude-telegram-relay/package.json` — Added dotenv@17.3.1

**Next steps:**
- Test voice message in Telegram
- Optional: Set up always-on service (launchd/systemd)
- Optional: Proactive check-ins & morning briefings

---

### 2026-02-14 — System Architecture Q&A: Model Usage, Knowledge Base Strategy, Database Organization

**Context:** Post-deployment discussion about optimal usage patterns, integration with work projects, and voice input capabilities.

**Q1: Which model does the bot use and how to track usage?**

**A1: Model & Usage Stats**
- **Model:** Bot calls Claude Code CLI without `--model` flag → uses default **Claude Sonnet 4.5**
- **Usage tracking:** Visit `claude.ai/account` → Usage tab (shows messages per model, costs)
- **Cost model:** Bot uses your Claude Code subscription/API credits
- **To change model:** Could modify `relay.ts:190` to add `--model opus` or `--model haiku`
- **Current setup:** Optimized for quality (Sonnet) over cost (Haiku not needed yet)

**Q2: Should the same system be used for work projects (robot navigation, SLAM, POMDP)?**

**A2: YES - Recommended Strategy**

**Decision:** Use Telegram bot + Supabase as unified personal knowledge base across all projects.

**Rationale:**
- Semantic search works across ALL conversations (work + personal)
- Database becomes "external brain" with vector embeddings
- Example: "What POMDP approach did I discuss 3 weeks ago?" → finds it via similarity
- The more domain knowledge added (robotics, SLAM, etc.), the smarter retrieval becomes

**Recommended workflow:**
1. Discuss work projects via Telegram bot (voice or text)
2. Liberal use of memory tags:
   - `[REMEMBER: Using FastSLAM2.0 with particle filter, 500 particles]`
   - `[REMEMBER: Sensor: Velodyne VLP-16 LiDAR]`
   - `[GOAL: Implement loop closure detection | DEADLINE: 2026-03-01]`
3. Query accumulated knowledge:
   - "Summarize my SLAM approach"
   - "What sensors am I using?"
   - "Show me all POMDP decisions I've made"
4. Result: Research lab notebook, but AI-searchable

**User's work context (for future reference):**
- **Project:** Autonomous robot navigation
- **Technologies:** SLAM (Simultaneous Localization and Mapping), POMDP (Partially Observable Markov Decision Process)
- **Use case:** Building knowledge base across work discussions

**Q3: Can work and personal use the same database?**

**A3: Two Options**

**Option A: Same Database, Different Channels (Recommended)**
- Use existing `messages.channel` and `messages.metadata` fields
- Example:
  ```sql
  -- Work messages
  INSERT INTO messages (content, channel, metadata)
  VALUES ('SLAM discussion...', 'work', '{"project": "robot-nav"}');

  -- Personal messages
  INSERT INTO messages (content, channel, metadata)
  VALUES ('Pizza preference...', 'personal', '{}');
  ```
- **Pros:**
  - Single database, easier management
  - Can search across contexts if needed
  - Cheaper (one Supabase project)
- **Cons:**
  - Work/personal data in same place (check company policy)

**Option B: Separate Databases for Work/Personal**
- Two Supabase projects with identical schemas
- **Pros:**
  - Complete isolation (better for sensitive work data)
  - Can delete one without affecting other
  - Complies with strict data policies
- **Cons:**
  - Two databases to manage
  - Can't search across contexts

**Recommendation:** Option A (same DB with channel tags) unless work data is highly sensitive.

**Q4: Can voice input be used when working in Claude Code sessions?**

**A4: Not Built-in, But Multiple Workarounds**

**Current state:**
- ✅ Telegram bot accepts voice → transcribes → responds (Groq Whisper)
- ❌ Claude Code CLI has no native voice input

**Workaround Options:**

**Option 1: Use Telegram Bot as Voice Interface (Already Working)**
- Send voice message to Telegram bot
- Bot transcribes via Groq
- Bot calls Claude Code with transcribed text
- Stores conversation in Supabase
- **Status:** Fully functional now

**Option 2: OS-Level Voice Input**
- **Linux:** `gnome-dictation` or `nerd-dictation` (hotkey → speak → text)
  ```bash
  sudo apt install gnome-dictation
  ```
- **macOS:** Built-in dictation (Fn key twice)
- **Windows:** Win+H for voice typing
- **Limitation:** OS-level, not Claude-aware

**Option 3: Hybrid Workflow**
- Keep Claude Code session open in terminal
- Send voice to Telegram bot with specific instructions
- Bot processes and remembers in Supabase
- Later reference in Claude Code: "What did I say about SLAM earlier?"

**Chosen approach:** Option 1 (Telegram bot) for voice input, with Option 2 as supplement for quick dictation.

**Key Decisions Made:**
1. ✅ Keep using Sonnet 4.5 (quality over cost for now)
2. ✅ Build unified knowledge base across work/personal projects
3. ✅ Use same Supabase database with channel metadata for organization
4. ✅ Use Telegram bot for voice input (already configured with Groq)
5. ✅ Consider OS-level voice input for terminal work

**Implementation Notes:**
- No code changes required (current setup supports all decisions)
- To organize by channel: Modify bot to detect work keywords and auto-tag `channel: "work"`
- To separate databases: Create second Supabase project, duplicate schema, point second bot instance to it

**Files affected:** None (this is strategic guidance, no code changes)

**Next steps:**
- Test voice message workflow on Telegram
- Start using `[REMEMBER]` tags for work knowledge
- Optional: Add auto-channel detection based on message content
- Optional: Set up always-on service for background operation

---
