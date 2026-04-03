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

### 2026-02-15 — Bot Session Continuity Debugging & Revert to Stable

**Context:** User reported bot losing conversation context between messages ("yes what?"). Attempted to fix session continuity, encountered multiple issues.

**Problem:** Bot wasn't maintaining conversation context across messages. Each message was treated as independent.

**Root Cause Investigation:**
1. Session ID not being saved to `~/.claude-relay/session.json`
2. Discovered Claude Code doesn't output "Session ID:" in response text
3. Found sessions are stored as UUID files in `~/.claude/projects/-home-lynnkse-cognitive-hq/`
4. Each `.jsonl` file is a session transcript

**Attempted Fixes (Failed):**
1. **Removed `--output-format text`** to capture session ID → No session ID in output
2. **Added debug logging** → Confirmed no "Session ID:" in stdout or stderr
3. **Fixed Bun spawn issue** → Added `node` prefix (Bun doesn't handle shebangs properly)
4. **Auto-resume latest session** → Attempted to read `~/.claude/projects/` directory
   - Used `await import("fs")` which doesn't work in Bun
   - Function `getLatestSessionId()` had syntax errors
5. **Catastrophic failure** → Bot started sending THIS session's responses to user on Telegram!
   - User received messages like "The relay needs write permission" and "Do you want me to: 1. Revert..."
   - Bot was somehow connected to the active Claude Code session

**Decision:** Revert all changes, restore original working bot.

**Actions Taken:**
1. Killed all running bot processes (`killall -9 bun`)
2. Reverted `claude-telegram-relay/src/relay.ts` to original via `git checkout`
3. Removed stale lock files
4. Restarted bot with original code

**Current Status:**
- ✅ Bot running (PID: 2287883)
- ✅ Responding to messages on Telegram
- ❌ No session continuity (each message is independent)
- ❌ User experiences: "What's my favorite color?" → "I don't have context"

**Technical Findings:**
- **Bun spawn limitation:** Doesn't handle shebang (`#!/usr/bin/env node`) properly, requires explicit `node` command
- **Claude Code session storage:** `~/.claude/projects/<project-name>/<uuid>.jsonl` files
- **Session resume mechanism:** `claude --resume <uuid>` expects UUID of existing session file
- **No auto-resume built-in:** Claude Code doesn't automatically resume sessions; relay must track/specify UUID

**Why Original Code Never Had Session Continuity:**
The `claude-telegram-relay` repo's session management was incomplete:
- Session tracking code existed (`session.sessionId`, `saveSession()`)
- But session ID extraction failed (regex never matched)
- `--output-format text` suppressed any potential session metadata
- Result: Fresh session for every message

**Lessons Learned:**
1. Test incrementally - don't make multiple changes at once
2. Bun spawn is not compatible with Node shebangs
3. Claude Code session architecture is file-based, not API-based
4. Session resume requires explicit UUID tracking
5. Changes to relay.ts require careful testing before deployment

**Open Questions:**
1. How should relay properly track and resume sessions?
   - Option A: Find latest session file in `~/.claude/projects/` before each call
   - Option B: Track session ID in a separate file and reuse
   - Option C: Accept no session continuity, rely on Supabase semantic search
2. Is conversation continuity even achievable given relay architecture?
   - Each `claude` CLI invocation is separate process
   - Resume reuses context but may hit token limits over time
3. Should we prioritize Supabase semantic search over session continuity?

**Recommendation:**
Use **Supabase semantic search** as the continuity mechanism instead of Claude sessions:
- Pro: Unlimited conversation history
- Pro: Works across bot restarts
- Pro: Already implemented and working
- Con: Not true "conversation" - fetches relevant past messages
- Con: Requires explicit [REMEMBER] tags for key facts

**Files Modified (then reverted):**
- `claude-telegram-relay/src/relay.ts` — Multiple failed attempts at session tracking

**Current Relay Code:** Original from github.com/godagoo/claude-telegram-relay

**Next Steps:**
1. Accept current bot behavior (no native session continuity)
2. Document for user how to use [REMEMBER] tags effectively
3. Test Supabase semantic search for "conversation-like" experience
4. Consider: Is true session continuity needed, or is semantic search sufficient?

---

### 2026-02-15 — Session Continuity WORKING: Simple Per-User Implementation

**Breakthrough:** User insight - THIS Claude Code session has no timeout. Why can't bot work the same way?

**Solution:** Per-user session tracking. No timeouts. Let Claude's context window auto-manage.

**Implementation:**
- Store session ID per user: `~/.claude-relay/sessions/<user_id>.json`
- Always resume user's session if it exists
- Never expire - sessions persist indefinitely like Claude Code CLI
- Added `node` prefix to spawn + `CLAUDECODE: undefined` env var

**Status:** ✅ WORKING - Bot now has true conversation continuity

**Files modified:** `claude-telegram-relay/src/relay.ts`

---

### 2026-03-29 — Finding: Persistent Process Solves Quadratic Token Growth (O(N²) → O(N))

**Context:** `--resume` with a persistent process is fundamentally different from `--resume` with per-message spawning.

**Per-message spawn (relay v1):**
```
spawn → load full transcript → process message → exit   (pays full replay cost)
spawn → load full transcript → process message → exit   (pays full replay cost again)
spawn → load full transcript → process message → exit   (pays full replay cost again)
```
Every message pays full transcript replay. Total cost = O(N²).

**Persistent process (relay v2):**
```
spawn → load full transcript once → stay alive
                                         → message 2 (no reload, context in memory)
                                         → message 3 (no reload)
                                         → message 4 (no reload)
```
Transcript loaded once on startup. All subsequent messages in the same process are free — context already in RAM. Total cost = O(N).

**Only exception:** if the process crashes and restarts, replay happens once. Still O(N), not O(N²).

The longer the session stays alive, the better the economics. This is the core reason the persistent process architecture solves the quadratic token problem.

---

### 2026-03-29 — First Implementation: pipe_session.py (Proof of Concept)

**Purpose:** Test whether Claude interactive mode works correctly when spawned with plain pipes instead of a real terminal.

**File:** `claude-telegram-relay/tools/pipe_session.py`

**What it does:**
- Spawns Claude with `stdin=PIPE, stdout=PIPE, stderr=PIPE`
- Three threads: keyboard→Claude stdin, Claude stdout→terminal, Claude stderr→terminal
- Each thread is an infinite blocking loop — blocks until data arrives, forwards it, loops
- Threads are `daemon=True` — die automatically when Claude process exits

**Usage:**
```bash
python3 claude-telegram-relay/tools/pipe_session.py                    # new session
python3 claude-telegram-relay/tools/pipe_session.py --resume <id>      # resume session
```

**Find current session ID:**
```bash
ls -t ~/.claude/projects/-home-lynnkse-cognitive-hq/*.jsonl | head -1
# filename without .jsonl is the session ID
```

**Known risk:** Claude may detect it's not a real terminal (no `/dev/pts/X`) and behave differently — garbled colors, missing readline, buffering issues. If this happens, fix is to use Python `pty` module (pseudoterminal) instead of plain pipes. Test plain pipes first.

**Status:** Written, not yet tested. Test by closing this session and running the script.

---

### 2026-03-29 — Architectural Decision: SessionManagerNode as stdin/stdout Multiplexer (Resolves Open Issue #1)

**Context:** How does SessionManagerNode control Claude's stdin while keeping the terminal connected?

**Resolution:** SessionManagerNode spawns Claude with pipes, then multiplexes all I/O through itself. Terminal stays fully connected — the node is invisible during direct CLI use.

**Architecture:**

```
keyboard ──────────────────┐
                           ▼
/user_input.sock ──► SessionManagerNode ──► Claude stdin (pipe)
                           ▲
                    queue (FIFO)              │
                                             ▼
terminal display ◄──────────────────── Claude stdout (pipe)
                                             │
                                             ▼
                                   /claude_response.sock
```

**What SessionManagerNode does:**
- Spawns Claude with `stdin=PIPE, stdout=PIPE` (owns the process)
- Reads from keyboard, forwards to Claude stdin
- Reads from `/user_input.sock` (Telegram/other frontends), forwards to Claude stdin
- Queue serializes ALL inputs (keyboard + bus) before reaching Claude stdin — one source at a time
- Reads from Claude stdout, forwards to both terminal display AND `/claude_response.sock`
- Session continuity preserved via `--resume <session_id>` on spawn

**Key property:** Terminal experience is identical to today — type, see responses. Node is invisible. Simultaneously, Telegram messages inject via socket and responses publish to bus.

**Linux file descriptor context:**
- Every Linux process has fd0 (stdin), fd1 (stdout), fd2 (stderr) — just file descriptors pointing to any file/pipe/socket
- By default they point to the terminal (`/dev/pts/X`)
- When spawned with `subprocess.Popen(stdin=PIPE, stdout=PIPE)`, they point to pipes owned by the parent
- Parent (SessionManagerNode) controls both ends — can forward to terminal AND to bus simultaneously

**Implementation sketch (Python):**
```python
proc = subprocess.Popen(
    ["claude", "--resume", session_id],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
)

# thread 1: keyboard → Claude stdin
# thread 2: /user_input.sock → queue → Claude stdin
# thread 3: Claude stdout → terminal display + /claude_response.sock
```

**Open issue #1 status: RESOLVED**
SessionManagerNode spawns Claude (not attaches). "Session is primary" reinterpreted as: session continuity (via --resume) is primary, not the process itself. Process is owned by SessionManagerNode but behaves identically from user perspective.

---

### 2026-03-28 — Architectural Decision: Hook Scripts in Python, Not Bash

**Decision:** Hook scripts (Stop, PermissionRequest, etc.) will be written in Python, not bash.

**Reason:**
- Hook tasks (parse `.jsonl` transcript, extract last assistant message, construct JSON payload, write to Unix socket) are fragile in bash (`jq` + `nc`)
- Python is cleaner, readable, properly handles errors
- Same language as the rest of the core bus logic
- Can import shared utilities from relay package later

**Hook contract (language-agnostic):**
- Receives event JSON on stdin
- Writes response JSON to stdout (only if influencing Claude's behavior)
- Exits with status code: 0 = success, 2 = block

**Any executable works in the `command` field:**
```json
"command": "python3 .claude/hooks/publish_response.py"
"command": ".claude/hooks/publish_response.sh"
"command": "node .claude/hooks/publish_response.js"
"command": ".claude/hooks/publish_response"  // compiled binary
```

**Hook script location:** `.claude/hooks/` directory

---

### 2026-03-28 — Architectural Decision: Claude Code Hooks — Key Properties

**Mental model:** Hook = software interrupt + blocking subprocess callback

- Event occurs (response complete, tool call, permission needed)
- Claude Code spawns hook script as subprocess ← callback
- `async: false` (default): Claude blocks, waits for hook exit, reads stdout/exitcode
- `async: true`: Claude continues immediately, hook runs in background, output ignored
- No preemption — Claude finishes current action fully before hook fires
- Closer to ROS callback in single-threaded spinner than hardware interrupt

**`async` decision per hook type:**
- `Stop` → `async: true` (publishing to bus is observational, must not slow session)
- `PermissionRequest` → `async: false` (Claude must wait for allow/deny before proceeding)
- `PreToolUse` → `async: false` (must validate/modify before tool runs)

**Always-on behavior:**
- Hook fires on every matching event in the session, including conversational responses
- Currently no Stop hook configured in this session (`.claude/settings.local.json` only has permissions)
- Once added, fires after every response — CLI and Telegram alike

**Response filtering implication:**
- Hook publishes everything to bus unconditionally
- RouterNode filters by `source` field — CLI messages stay in terminal, Telegram messages route to Telegram
- No need for special sentinel variants per interface

**How to add Stop hook to `settings.local.json`:**
```json
{
  "permissions": { "allow": [...], "deny": [] },
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/publish_response.py",
        "async": true
      }]
    }],
    "PermissionRequest": [{
      "hooks": [{
        "type": "command",
        "command": "python3 .claude/hooks/permission_request.py"
      }]
    }]
  }
}
```

**Settings file scope:**
| File | Scope | Git |
|------|-------|-----|
| `.claude/settings.json` | Project, shared | Yes |
| `.claude/settings.local.json` | Project, machine-local | No |
| `~/.claude/settings.json` | All projects on machine | No |

Hook scripts go in `.claude/hooks/` — machine-specific paths → `settings.local.json` is the right home.

---

### 2026-03-28 — Architectural Decision: Dynamic Permission Routing in Relay v2

**Context:** How does tool permission approval work when Claude is accessed via Telegram bot?

**v1 approach: static pre-approval**
Hardcoded allowlist in `.claude/settings.local.json`:
- `Read`, `Edit`, `Write` — always allowed
- `Bash` — only specific commands (`tree`, `ls`, `find`, `chmod`, `git add`, one specific `git commit`)
- Everything else — blocked or prompts in terminal (unreachable from bot)

**v2 approach: dynamic per-request routing via PermissionRequest hook**

Claude Code's `PermissionRequest` hook fires before each tool call that requires approval. Hook intercepts it, routes through the bus to the originating interface:
- **Telegram** → inline keyboard buttons [Allow] [Deny]
- **CLI** → normal terminal prompt

```
Claude wants to run: git push
        │
PermissionRequest hook
        │
/permission_request.sock  →  RouterNode  →  Telegram inline buttons
                                                    │
                                             user taps [Allow]
                                                    │
/permission_response.sock  →  SessionManagerNode  →  hook returns decision
        │
Claude proceeds or aborts
```

New topics needed on the bus:
- `/permission_request` — `{tool_name, tool_input, source, user_id, request_id}`
- `/permission_response` — `{request_id, decision: "allow"|"deny"}`

**Comparison:**

| | v1 | v2 |
|--|--|--|
| Mechanism | Static allowlist | Dynamic per-request hook |
| Approval | Pre-approved at config time | Real-time per tool call |
| User sees | Nothing | Exact command before approving |
| Dangerous commands | Blocked by omission | Routed for explicit approval |
| Flexibility | Rigid | Dynamic |

**Open question: unattended timeout policy**

If a permission request arrives and the user doesn't respond (asleep, away), what is the default?
- Auto-deny after N seconds — safe but blocks Claude mid-task
- Auto-allow for low-risk tools (Read) — risky if policy is wrong
- Queue the request, notify user, Claude waits — cleanest but requires Claude to not timeout

This is a policy decision, not an architecture decision. Needs explicit design before implementation.

**Status:** Design only.

---

### 2026-03-28 — Architectural Decision: Runtime and Transport for Relay v2

**Bus transport:** Unix domain sockets (not named pipes)
- Path: `/tmp/cognitive-hq/user_input.sock`, `/tmp/cognitive-hq/claude_response.sock`
- Reason: supports multiple readers (debug monitor, future multi-session), same API as TCP sockets — swap address family when/if multi-machine architecture is needed
- Wire format: newline-delimited JSON

**Runtime split:**
- **Python** — SessionManagerNode, RouterNode, MemoryNode (core bus logic)
- **Bun/TypeScript** — TelegramNode only (already written, grammY is Node-native)
- Components communicate via Unix sockets — runtime boundary doesn't matter

**Why Python for core:**
- User wrote Python agent from scratch (105 tests) — deep familiarity
- SessionManagerNode owns Claude process lifecycle (crashes, restarts, pipe management) — want a trusted runtime
- Bun has a known subprocess/shebang issue (Claude CLI uses `#!/usr/bin/env node`, Bun doesn't honor it correctly) — already hit this in v1, don't want it in the critical path
- Python `subprocess` is robust and well understood for process management

**Why keep Bun for Telegram:**
- TelegramNode already written and working
- grammY is Node-native
- No process management complexity in TelegramNode

---

### 2026-03-28 — Architectural Decision: Claude Code Stop Hook as Session-to-Bus Bridge

**Context:** How does a pre-existing Claude CLI session attach to the Relay v2 bus without special launch procedures?

**Decision: Use the `Stop` hook as the publish bridge**

Claude Code's `Stop` hook fires after every complete response turn. It receives `transcript_path` — the path to the live `.jsonl` session file. A hook script reads the last assistant message and writes it to the bus (Unix socket or named pipe).

```json
// .claude/settings.json
{
  "hooks": {
    "Stop": [{
      "hooks": [{
        "type": "command",
        "command": ".claude/hooks/publish_response.sh",
        "async": true
      }]
    }]
  }
}
```

```bash
# publish_response.sh
input=$(cat)  # JSON from stdin, includes transcript_path
transcript=$(echo "$input" | jq -r '.transcript_path')
last_response=$(tail -n1 "$transcript" | jq -r '.message.content[-1].text')
echo "$last_response" | nc -U /tmp/claude_response.sock
```

For input: bus writes directly to Claude's stdin via pipe, or `UserPromptSubmit` hook intercepts injected messages.

**Why this is clean:**
- Session needs no special launch procedure
- Hook is invisible during direct terminal use
- When relay is listening on the socket, messages flow automatically
- Session lifecycle is fully independent of relay lifecycle

**Caveats:**
- `Stop` also fires on interrupts — need `stop_hook_active` check to avoid loops
- Should verify sentinel token presence before publishing to bus
- Hook fires per-turn, not per-tool-call — correct granularity for our use case

**Relevant hook events (full list reviewed):**
- `Stop` — end of Claude's response turn ← primary bridge hook
- `UserPromptSubmit` — fires when user submits input, can inject context
- `PostToolUse` — fires after each tool call (finer granularity, not needed here)
- `SessionStart` — fires on session start/resume, useful for relay registration

**Status:** Design only. Hook script to be implemented in Relay v2.

---

### 2026-03-28 — Session Continuity Note: Context for Resuming This Design Session

**Purpose:** Capture everything needed to continue Relay v2 design from a fresh session.

**What was designed in this session (2026-03-28):**

All decisions are logged in LOG.md under 2026-03-28 entries. Read them in this order:
1. Quadratic token growth finding (--resume replay is O(N²))
2. Persistent Claude process + sentinel token decision
3. Multi-frontend single-backend decision
4. Terminal multiplexer / TUI decision
5. ROS-style node graph decision ← canonical architecture
6. Stop hook as session-to-bus bridge ← this entry

**The canonical Relay v2 architecture (summary):**

```
[Claude CLI session] — pre-existing, independent lifecycle
        │
        │ Stop hook → publish_response.sh → Unix socket
        │ UserPromptSubmit hook ← messages from bus
        │
   [Unix socket bus]   (/tmp/claude_response.sock, /tmp/user_input.sock)
        │
SessionManagerNode
  - owns bus
  - queues messages FIFO per user
  - routes responses back to originating interface
        │
┌───────┼───────┐
│       │       │
TelegramNode  CLINode  VoiceNode(later)
(grammY)      (stdin)  (phone)
        │
MemoryNode (async, non-blocking)
  - Supabase writes
  - semantic search
```

**Key decisions to remember:**
- Session is primary, relay attaches to it — not the other way around
- Sentinel token (`<<RELAY_END_<uuid>>>`) in system prompt marks end of every response
- Queue serializes concurrent messages from all frontends; response tagged with source for routing
- Implementation: in-process event emitter first, upgrade to Redis if multi-process needed
- Bus: Unix domain sockets preferred over named pipes (multi-reader, bidirectional)
- Testing: manual pub/sub to sockets (equivalent to `rostopic pub` / `rostopic echo`)
- Node graph is the pattern; actual ROS not required

**Current repo state:**
- Working branch: `claude-telegram-relay` repo on branch `relay-v2`
- Existing relay: `claude-telegram-relay/src/relay.ts` (v1, fully working)
- All design decisions: `.claude/LOG.md` (this file), `.claude/TODO.md`
- Relay v2 TODO entry: `.claude/TODO.md` → "Relay v2: persistent Claude process per user + sentinel token protocol"

**All decisions (2026-03-28/29) in LOG.md — full reading order:**
1. Quadratic token growth finding (O(N²) with --resume per-message spawn)
2. Persistent Claude process + sentinel token decision
3. Multi-frontend single-backend decision
4. Terminal multiplexer / TUI decision
5. ROS-style node graph decision ← canonical architecture
6. Stop hook as session-to-bus bridge
7. Runtime and transport (Python core, Bun TelegramNode, Unix sockets, NDJSON)
8. Dynamic permission routing (PermissionRequest hook → Telegram inline buttons)
9. Hook scripts in Python (not bash)
10. Hook key properties (async for Stop, blocking for PermissionRequest)
11. Persistent process solves O(N²) → O(N) ← important finding
12. pipe_session.py proof of concept ← first implementation artifact
13. SessionManagerNode as stdin/stdout multiplexer ← resolves open issue #1

**Updated architecture (supersedes original sketch above):**
```
SessionManagerNode (Python)
  - spawns Claude with stdin=PIPE, stdout=PIPE
  - multiplexes: keyboard + /user_input.sock → Claude stdin (via FIFO queue)
  - multiplexes: Claude stdout → terminal display + /claude_response.sock
  - session continuity via --resume on spawn
        │
   Unix socket bus
   /tmp/cognitive-hq/user_input.sock
   /tmp/cognitive-hq/claude_response.sock
   /tmp/cognitive-hq/permission_request.sock  (future)
   /tmp/cognitive-hq/permission_response.sock (future)
        │
┌───────┼───────────┐
TelegramNode    CLINode    VoiceNode(later)
(Bun/grammY)   (stdin)
        │
MemoryNode (Python, async Supabase writes)
```

**Open issues remaining:**
- #2: Sentinel injection — who injects it and when (CLAUDE.md? SessionStart hook? manual?)
- #3: Unattended permission policy — auto-deny after timeout? queue indefinitely?
- #4: Multi-user process registry — one SessionManagerNode, multiple Claude processes
- #5: PermissionRequest bus flow — request_id correlation, dedicated sockets

**Current repo state:**
- Branch: `claude-telegram-relay` on `relay-v2`
- First artifact: `claude-telegram-relay/tools/pipe_session.py` (written, not yet tested)
- v1 relay untouched: `claude-telegram-relay/src/relay.ts`

**Immediate next step:** Close this session, run `pipe_session.py`, verify terminal experience is identical to running `claude` directly. Watch for pty issues (garbled colors, missing readline).

**To resume:** Read BOOTSTRAP.md, read LOG.md 2026-03-28/29 entries in order above, read TODO.md Relay v2 entry.

---

### 2026-03-28 — Architectural Decision: ROS-Style Node Graph for Relay v2

**Context:** User has ROS background (robotics/SLAM). The multi-frontend session manager maps cleanly onto a ROS-style pub/sub node graph.

**Decision: Model Relay v2 as a node graph with topics**

```
TelegramNode
  sub: Telegram API (grammY)
  pub: /user_input {text, source:"telegram", user_id, media_path?}

CLINode
  sub: stdin
  pub: /user_input {text, source:"cli", user_id}

VoiceNode (later)
  sub: phone call stream
  pub: /user_input {text, source:"voice", user_id}

         /user_input topic
                │
                ▼
SessionManagerNode
  sub: /user_input
  - owns Claude process (stdin/stdout)
  - maintains FIFO queue per user
  - writes to Claude stdin
  - reads stdout until sentinel token
  pub: /claude_response {text, source, user_id}

         /claude_response topic
                │
                ▼
RouterNode
  sub: /claude_response
  - routes by source field
  pub: /telegram_outbox
  pub: /cli_outbox
  pub: /voice_outbox (later)

MemoryNode
  sub: /user_input, /claude_response
  - saves to Supabase async (non-blocking)
  - no effect on main pipeline latency
```

**Why this pattern fits:**
- Queue per user falls out naturally from topic message ordering
- New frontend = new node publishing to `/user_input`, nothing else changes
- MemoryNode is fully decoupled — Supabase writes are async, don't block the main pipeline
- RouterNode is thin — reads `source` field, forwards to correct outbox
- Each node is independently restartable

**Implementation note:** Actual ROS not required. The node graph is the architectural pattern, not the runtime. Can implement with:
- In-process event emitter (simplest)
- Redis pub/sub (if multi-process)
- Any queue library

**Relation to previous decisions:**
- SessionManagerNode owns the persistent Claude process + sentinel protocol (LOG.md 2026-03-28)
- RouterNode handles response routing back to originating interface (LOG.md 2026-03-28)
- TUI/multiplexer (LOG.md 2026-03-28) sits inside CLINode as its output renderer

**Status:** Design only. Supersedes the simpler "process manager + bot agent" sketch from earlier today.

---

### 2026-03-28 — Architectural Decision: Terminal Multiplexer / TUI for Multi-Frontend Visibility

**Context:** In Relay v2, all interfaces (CLI, Telegram, voice) share one Claude process. This means Telegram messages and their responses will print inline in the terminal session, mixing with CLI work.

**Finding: Shared stdin/stdout is both a feature and a UX problem**

Properties of shared process:
- Every Telegram message is visible in the terminal in real time
- Claude's response builds in the terminal before being routed to Telegram
- Terminal can serve as a debug/monitor view for all bot activity
- But: Telegram responses printing mid-CLI-conversation is jarring

**Decision: Terminal multiplexer (TUI) to visually separate interface streams**

Each frontend gets its own pane in a TUI / tmux-style interface. All panes feed the same Claude session underneath.

```
┌─ CLI input/output ──────────────────┐
│ > how does the relay work?          │
│ The relay is a Telegram bot that... │
└─────────────────────────────────────┘
┌─ Telegram [Lynn, voice] ────────────┐
│ [transcribed]: remind me to call... │
│ Sure, I'll remind you at 3pm...     │
└─────────────────────────────────────┘
```

**Implementation options:**
- `tmux` with named panes — each interface writes to its own pane
- Python/Node TUI library (e.g. `blessed`, `ink`) — custom layout
- Simple approach: prefix each line with source tag (`[TG]`, `[CLI]`) and let the user filter/split manually

**Status:** Design only. Lower priority than core Relay v2 components. Can be added incrementally after the session manager and queue are working.

---

### 2026-03-28 — Architectural Decision: Multi-Frontend Single-Backend Session Architecture

**Context:** Designing Relay v2. User needs to use CLI and Telegram bot simultaneously, not as alternatives.

**Finding: Concurrent multi-frontend usage is a real requirement**

Usage patterns:
- **CLI** — preferred for code work, file edits, confirmations
- **Telegram bot** — preferred for voice notes, images, mobile/on-the-go
- **Phone/voice call** — planned future interface
- These are used **simultaneously**, not exclusively

This rules out a simple "either/or" lock. The architecture must support multiple interfaces sending to the same Claude session concurrently.

**Decision: Multi-frontend, single-backend with serialized queue**

```
CLI ──────────────────┐
Telegram bot ─────────┼──► session manager ──► Claude process (stdin/stdout)
Phone/voice (later) ──┘         │
                                 └──► routes response back to originating interface
```

Each interface submits messages to a shared queue. The session manager processes one message at a time (Claude is inherently single-threaded per session) and routes each response back to the interface that sent it.

**Queue semantics:**
- Messages tagged with source interface on enqueue
- Processed strictly in order (FIFO)
- Response routed back to originating interface only
- If CLI and Telegram both enqueue before Claude finishes — second waits, gets its response when processed

**Decision: Queue-based concurrency (not lock-based)**

A lock file (`<session_id>.lock`) would prevent collision but doesn't handle the multi-frontend case cleanly. A queue is the right primitive — it serializes access while preserving message ordering and response routing.

**Status:** Design only. Informs Relay v2 implementation.

---

### 2026-03-28 — Architectural Decision: Persistent Claude Process + Sentinel Token for Relay v2

**Context:** Designing next-generation relay architecture to replace the current per-message `--resume` spawn approach.

**Decision: Persistent Claude process per user**

Keep one `claude` CLI process alive per user, communicating via stdin/stdout pipes instead of spawning a new process per message. This eliminates the quadratic token growth problem (see finding below).

```
Telegram → Bot Agent → stdin pipe → [claude process] → stdout pipe → Bot Agent → Telegram
```

**Decision: Sentinel token for end-of-response detection**

Claude is instructed via system prompt to always terminate every response with a unique sentinel token. The bot reads stdout until it sees the sentinel, then strips it and sends the response.

Example sentinel: `<<RELAY_END_7f3a>>` (collision-resistant, generated at startup)

Rules:
- Sentinel must be unique enough to never appear naturally in output (avoid `##END##`, use a UUID-based token)
- If sentinel never arrives → crash or system prompt failure → restart Claude process, do not silently retry
- Timeout as fallback — needed during long tool executions (bash, file reads, API calls)
- On timeout: send partial response with warning rather than dropping entirely

**Why CLI, not API:**
- Need Claude Code tool access (Read, Edit, Write, Bash, MCP) for files, web search, databases, Google Drive, Jira, etc.
- Running on Pro subscription (monthly flat rate) — API is per-token billing, not viable

**Architecture sketch:**
```
Per-user process manager
├── user_123: claude process (stdin/stdout pipes, stream-json)
│     └── message queue (serialize concurrent messages)
├── user_456: claude process
└── ...

Bot agent
├── receives Telegram message
├── routes to user's process manager
├── enqueues message → writes to stdin
├── reads stdout until sentinel (or timeout)
└── sends response to Telegram
```

**Status:** Design only. Current relay remains in place until this is built.

---

### 2026-03-28 — Finding: Quadratic Token Growth in --resume Session Replay

**Observation:** The relay's session continuity mechanism (`claude --resume <session_id>`) causes O(N²) token consumption across a conversation.

**Mechanism:**
- `--resume` loads the full `.jsonl` session transcript into context on every invocation
- Claude CLI exits after each message; there is no persistent process
- Each new message pays the token cost of all prior turns

**Consequence:** A token sent in message 1 is loaded into the LLM on every subsequent message. By message N, it has been paid for N times. Total tokens consumed across a conversation of N turns grows quadratically, not linearly.

**Example (500 tokens/turn):**
- Message 10: 5,000 tokens sent (including 9 prior turns)
- Message 100: 50,000 tokens sent (including 99 prior turns)
- Total across 100 messages: ~2.5 million tokens vs ~50k for linear

**Compounding factor:** Supabase semantic context (FACTS + GOALS + top-5 relevant messages) is injected on top of the full session replay — so the prompt is even larger than replay alone.

**Current risk level:** Low for occasional use. Will become expensive and slow under heavy daily use.

**Standard mitigation:** Sliding window (keep last K turns verbatim) + summarization of older turns + semantic search for specific facts. Drop full replay beyond the window.

---

### 2026-04-03 — Relay v2 Open Questions Resolved

All 15 open questions closed. Ready to implement.

| # | Question | Decision |
|---|----------|----------|
| 1 | Sentinel injection | `--append-system-prompt` at spawn (flag confirmed exists) |
| 2 | CLINode input mode | Raw mode — feel identical to direct claude session |
| 3 | display.sock | One CLINode at a time |
| 4 | File location | `claude-telegram-relay/relay_v2/` |
| 5 | MemoryNode | In-process with SessionManagerNode |
| 6 | Unattended permissions | Deferred to phase 2 |
| 7 | Multi-user | Single user first |
| 8 | Proactive always-on | Yes, 24/7 in tmux |
| 9 | ProactiveNode HTTP | Local only (`localhost:PORT`); public IP option later |
| 10 | Proactive silence | Prompt instruction ("stay silent if nothing needs attention") |
| 11 | MCPs | Supabase first, rest added gradually |
| 12 | Media cleanup | TelegramNode owns downloaded files, cleans up after response delivered |
| 13 | Profile injection | `--append-system-prompt` at spawn (same as sentinel) |
| 14 | Typing keepalive | TelegramNode sends every 4s while waiting for response |
| 15 | Config location | Reuse `claude-telegram-relay/.env`; revisit if multi-agent needed |

**Note on Q2 (raw mode):** CLINode puts its own stdin into raw mode and forwards every byte to SessionManagerNode → Claude's PTY. Indistinguishable from running `claude` directly.

**Note on Q11 (Supabase MCP):** Configure as a separate task before or alongside Phase 2 (MemoryNode). Once active, Claude stores/retrieves memories directly — tag system becomes fallback.

**Note on Q15 (multi-agent):** If two agents need to run simultaneously on the same machine in future, config split and socket namespace separation will be needed. Deferred.

---

### 2026-04-02 — Relay v2 Architecture Design Session

**Context:** Full design session for relay v2. Covers SessionManagerNode, CLINode, ProactiveNode, MCP strategy, and v1 code review findings.

---

#### SessionManagerNode Design

Owns the persistent Claude process. All other nodes are clients.

**PTY mechanics:**
```python
master_fd, slave_fd = pty.openpty()
proc = subprocess.Popen(cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)
os.close(slave_fd)
# read/write master_fd
```

**Thread layout:**
- **PTY reader thread** — reads `master_fd`, forwards raw bytes to display.sock (CLINode), accumulates response buffer, detects sentinel → strips it, signals IDLE, publishes to `claude_response.sock`
- **Queue processor thread** — state machine (IDLE/GENERATING). IDLE: dequeue next message, write to `master_fd` → GENERATING. GENERATING: blocks on `threading.Event` until reader signals sentinel found.
- **Socket listener thread** — accepts NDJSON on `user_input.sock`, enqueues with `(source, user_id, text, media_path?)`
- **Display server thread** — accepts single CLINode connection on `display.sock`, streams raw PTY bytes

**State machine:**
```
IDLE → (dequeue + write to master_fd) → GENERATING → (sentinel found) → IDLE
```

**Session ID tracking:** After spawn, find newest `.jsonl` in `~/.claude/projects/-home-lynnkse-cognitive-hq/`. Store in `~/.claude-relay/session_id`. Pass `--resume` on crash restart.

**PTY size:** CLINode sends terminal size on connect. SessionManager calls `ioctl(master_fd, TIOCSWINSZ, ...)`. CLINode forwards `SIGWINCH`.

---

#### CLINode Design

Dead simple — two threads:
- **Display thread** — connect to `display.sock`, read raw bytes, write to `sys.stdout`
- **Input thread** — read lines from `sys.stdin`, send NDJSON to `user_input.sock`

CLINode is ~50 lines. All complexity in SessionManagerNode.

---

#### Socket Protocol

```
/tmp/cognitive-hq/
├── user_input.sock       — frontends → SessionManager, NDJSON: {text, source, user_id, media_path?}
├── claude_response.sock  — SessionManager → RouterNode, NDJSON: {text, source, user_id}
└── display.sock          — SessionManager → CLINode, raw PTY bytes (streaming)
```

**ANSI handling:** display.sock carries raw bytes including ANSI (CLINode displays as-is). `claude_response.sock` carries ANSI-stripped clean text (for Telegram). Sentinel stripped from both.

---

#### ProactiveNode Design

Two trigger mechanisms:
1. **Cron scheduler** — fires on schedule, injects prompt into `user_input.sock` with `source: "proactive"`
2. **Event queue** — HTTP endpoint accepts POSTs from external systems (Slack, email, webhooks), wraps as NDJSON and sends to `user_input.sock`

RouterNode routes responses with `source: "proactive"` → Telegram always (user may not be at terminal).

Claude decides whether to respond or stay silent ("stay silent if nothing needs attention").

All nodes assumed 24/7 in tmux sessions. Persistent Claude process stays alive for weeks like current Claude Code sessions.

---

#### Memory Architecture (v2 vs v1)

**v1 pattern (kept for v2):**
- Output tags: `[REMEMBER: fact]`, `[GOAL: text | DEADLINE: date]`, `[DONE: search text]`
- MemoryNode extracts tags from `claude_response.sock`, writes to Supabase, strips from display
- Per-message input enrichment: prepend FACTS + GOALS + top-5 semantic matches before message enters queue

**v2 change:** enrichment happens in MemoryNode as preprocessing before SessionManagerNode queue, not in TelegramNode. All frontends benefit.

**MCP path:** No MCPs configured currently. Once Supabase MCP is configured, Claude can store/retrieve memories directly — tag system becomes fallback. RouterNode still strips tags regardless.

---

#### V1 Code Review Findings (relay.ts, memory.ts, transcribe.ts)

Key things v1 does that v2 must account for:

1. **Media handling** — images and documents downloaded to disk, path injected into message text (`[Image: /path]`, `[File: /path]`). Voice transcribed via Groq/whisper before entering queue. Cleanup after Claude responds — responsibility needs assigning (TelegramNode owns the file, so TelegramNode cleans up after `claude_response.sock` delivers).

2. **Typing indicator keepalive** — Telegram typing indicator expires after ~5s. TelegramNode must send `replyWithChatAction("typing")` every 4s while waiting for response from `claude_response.sock`.

3. **Profile + persona** — v1 injects `config/profile.md` + current time + user name into every prompt via `buildPrompt()`. In v2 with persistent process, profile belongs in system prompt at spawn time. Only current time and memory context need per-message injection.

4. **Telegram 4096 char limit** — split at natural boundaries (paragraph → line → word). RouterNode handles this.

5. **Session ID from JSON output** — v1 uses `--output-format json` to get `session_id` from Claude. Not available in interactive mode. V2 uses filesystem approach (already in v1 as `findLatestSession()`).

6. **Lock file** — v1 prevents multiple instances. SessionManagerNode should do the same.

---

#### Open Questions (full list as of 2026-04-02)

| # | Question | Status |
|---|----------|--------|
| 1 | Sentinel injection — `--system-prompt` flag or CLAUDE.md? | Needs testing |
| 2 | CLINode input mode — line-buffered or raw? | Proposed: line-buffered first |
| 3 | display.sock — one CLINode at a time or multiple? | Proposed: one at a time |
| 4 | File location — `relay_v2/` dir? | Proposed: `claude-telegram-relay/relay_v2/` |
| 5 | MemoryNode in-process or separate? | **Decided: in-process** |
| 6 | Unattended permission timeout policy | Deferred to phase 2 |
| 7 | Multi-user now or single user first? | **Decided: single user first** |
| 8 | Proactive messages — always-on or lightweight spawner? | **Decided: always-on, 24/7 assumption** |
| 9 | ProactiveNode HTTP endpoint — local only or externally reachable? | Open |
| 10 | Proactive silence — prompt instruction or pre-check? | Open |
| 11 | Which MCPs to configure first? | Proposed: Supabase first |
| 12 | Media cleanup — who deletes downloaded files after Claude responds? | Proposed: TelegramNode |
| 13 | Profile injection — CLAUDE.md or `--system-prompt` at spawn? | Depends on Q1 |
| 14 | Typing indicator keepalive — TelegramNode sends every 4s while waiting? | Proposed: yes |

---

#### Implementation Order

1. `session_manager.py` + `cli_node.py` — working terminal session through manager
2. `memory_node.py` — input enrichment + output tag extraction
3. `router_node.py` + TelegramNode integration (port from relay.ts)
4. `proactive_node.py` — cron + HTTP endpoint

---

### 2026-04-02 — Finding: PTY Required (Not Plain Pipes); pipe_session.py Working

**Result:** pipe_session.py works. This session is running through it.

**Key finding:** Claude CLI requires a real TTY. When stdin is a plain pipe, Claude detects it's not a terminal and enters `--print` mode (non-interactive). `pty.spawn()` solves this by providing a real PTY.

**Implication for SessionManagerNode:** Must use `pty.openpty()` master/slave pair, not `subprocess.Popen(stdin=PIPE, stdout=PIPE)`.

**Path forward (already documented in pipe_session.py):**
```python
master_fd, slave_fd = pty.openpty()
proc = subprocess.Popen(cmd, stdin=slave_fd, stdout=slave_fd, stderr=slave_fd)
os.close(slave_fd)
# read/write master_fd to multiplex programmatic + keyboard I/O
```
`master_fd` is bidirectional — write to send input to Claude, read to receive Claude's output.

**Status:** Unblocks SessionManagerNode implementation.

---
