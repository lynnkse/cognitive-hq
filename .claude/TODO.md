# TODO — cognitive-hq Project Tasks

This file tracks active, pending, and completed tasks for the cognitive-hq project.
It is the authoritative source for task management alongside LOG.md.

---

## Active Tasks

*No active tasks currently.*

---

## Pending Tasks

### [ ] Build Claude Code hook for Supabase memory extraction
**Priority:** HIGH
**Created:** 2026-02-17

Build a Claude Code hook that automatically extracts memories/facts from Claude Code sessions and writes them to the unified Supabase database — enabling a cognitive blueprint that spans both personal (Telegram bot) and work (Claude Code) sessions.

**Goal:** Unified cross-cutting knowledge base, not project-based silos.

**Reference:** GOAL logged in bot memory.

---

### [ ] Set up proactive check-ins and morning briefing
**Priority:** MEDIUM
**Created:** 2026-02-17

Enable smart check-ins and daily briefings using example scripts in `claude-telegram-relay/examples/`.

**Guide:** `claude-telegram-relay/CLAUDE.md` Phase 6

---

### [ ] Unify TODO files
**Priority:** MEDIUM
**Created:** 2026-02-17

Consolidate task tracking back into a single `.claude/TODO.md`. Currently the bot has permission to edit this file directly, so a separate TODO_ACTIVE.md is not needed.

---

### [ ] Relay v2: persistent Claude process per user + sentinel token protocol
**Priority:** MEDIUM
**Created:** 2026-03-28

Replace the current per-message spawn architecture with a persistent Claude CLI process per user communicating via stdin/stdout pipes. See LOG.md 2026-03-28 for full design.

**Architecture: ROS-style node graph (see LOG.md 2026-03-28)**

Nodes:
1. **TelegramNode** — grammY subscriber, publishes to `/user_input`
2. **CLINode** — stdin subscriber, publishes to `/user_input`
3. **VoiceNode** (later) — phone call stream, publishes to `/user_input`
4. **SessionManagerNode** — owns persistent Claude process; FIFO queue per user; sentinel protocol; publishes to `/claude_response`
5. **RouterNode** — routes `/claude_response` back to originating interface by `source` field
6. **MemoryNode** — async Supabase writes; subscribes to `/user_input` + `/claude_response`; non-blocking

Message schema on `/user_input`: `{text, source, user_id, media_path?}`
Message schema on `/claude_response`: `{text, source, user_id}`

Sentinel: system prompt requires `<<RELAY_END_<uuid>>>` at end of every response. Missing sentinel = crash/error → restart Claude process.

Implementation: node graph is the pattern, not the runtime. Start with in-process event emitter; upgrade to Redis pub/sub if multi-process needed.

**Multi-frontend requirement:** CLI and Telegram used simultaneously. CLI for code/files; Telegram for voice, images, mobile. Phone/voice call planned.

**Open issues before full implementation:**
- [ ] #2: Sentinel injection — who injects `<<RELAY_END_<uuid>>>` and when
- [ ] #3: Unattended permission policy — what happens if PermissionRequest gets no response
- [ ] #4: Multi-user process registry design
- [ ] #5: PermissionRequest bus flow — dedicated sockets, request_id correlation

**First artifact:** `claude-telegram-relay/tools/pipe_session.py` — proof of concept, spawns Claude with pipes, multiplexes keyboard↔Claude.

**[ ] Test pipe_session.py**
- Close this session
- Run: `python3 claude-telegram-relay/tools/pipe_session.py --resume <session_id>`
- Find session ID: `ls -t ~/.claude/projects/-home-lynnkse-cognitive-hq/*.jsonl | head -1`
- Verify: terminal experience identical to running `claude` directly
- Watch for: garbled colors, missing readline, buffering issues → if any, switch to `pty`
- Report findings back to LOG.md

**Reference:** LOG.md 2026-03-28/29 — full reading order in Session Continuity Note

**Supersedes:**
- `[ ] Fix quadratic token growth` (below) — that task becomes redundant if this is built

**Reference:** LOG.md 2026-03-28 — Architectural Decision: Persistent Claude Process + Sentinel Token

---

### [ ] Fix quadratic token growth: replace --resume full replay with sliding window
**Priority:** MEDIUM
**Created:** 2026-03-28

**Problem:** `--resume` replays the full session transcript on every message, causing O(N²) token consumption. A token from message 1 is paid for on every subsequent message. See LOG.md 2026-03-28 for full analysis.

**Solution:** Replace full session replay with:
1. Sliding window — pass only last K turns verbatim to Claude (drop `--resume`, build prompt manually)
2. Summarization — compress turns older than K into a short summary block
3. Semantic search — already implemented (Supabase), handles specific fact retrieval

**Files to change:** `claude-telegram-relay/src/relay.ts` (`callClaude`, `buildPrompt`)

**Risk:** Losing `--resume` means losing Claude's native session mechanism. Need to manually manage conversation history in the prompt.

---

### [ ] Fix bot session continuity (deferred)
**Priority:** MEDIUM
**Created:** 2026-02-15
**Status:** Attempted and reverted, needs different approach

**Problem:** Bot loses conversation context between messages.

**Attempted solutions (all failed - see LOG.md 2026-02-15):**
- Session ID extraction from Claude output
- Auto-resume from ~/.claude/projects/ directory
- Result: Catastrophic failure, bot reverted to original code

**Current workaround:** Supabase semantic search + [REMEMBER] tags

**Future options:**
- Properly implement session file tracking (requires Bun compatibility fixes)
- Accept semantic search as primary continuity mechanism
- Investigate Claude Code API alternatives

---

### [ ] Review learning queue for implementation candidates
**Priority:** LOW
**Created:** 2026-02-14

Periodically review `.claude/LEARNING_QUEUE.md` for items worth implementing.

**Process:**
1. Capture interesting concepts from courses to Inbox
2. Evaluate and move to Research/Implement/Archive
3. For "Implement" items, create specific tasks in this TODO
4. Link back to learning queue entry for context

**Reference:** `.claude/LEARNING_QUEUE.md`

---

### [ ] Optional: Auto-channel detection for work/personal
**Priority:** LOW
**Created:** 2026-02-14

Add automatic channel tagging to relay.ts based on message content.

**Implementation:**
- Detect work keywords: "SLAM", "POMDP", "robot", "navigation", "particle filter"
- Auto-set `channel: "work"` and `metadata: {"domain": "robotics"}`
- Personal keywords: "food", "workout", "personal"
- Default: `channel: "telegram"`

**File:** `claude-telegram-relay/src/memory.ts` (add keyword detection)

---

### [ ] Optional: Install OS-level voice input for terminal
**Priority:** LOW
**Created:** 2026-02-14

Set up gnome-dictation or nerd-dictation for voice-to-text in terminal.

```bash
sudo apt install gnome-dictation
# Configure hotkey in system settings
```

**Use case:** Quick voice input when working in Claude Code terminal session (supplement to Telegram bot voice)

---


### [ ] Future: Deploy relay to always-on service
**Priority:** LOW
**Created:** 2026-02-14

Configure as background service (launchd/systemd/PM2) for auto-start on boot.

**Guide:** `claude-telegram-relay/CLAUDE.md` Phase 5

---

### [ ] Future: Integrate .claude/ context into relay prompts
**Priority:** MEDIUM
**Created:** 2026-02-14

Modify `buildPrompt()` in relay.ts to include project context from .claude/ files:
- BOOTSTRAP.md, RULES.md (if PROJECT_DIR has .claude/)
- Recent LOG.md entries (last 10)
- Active TODO.md tasks

This would make the bot project-aware and able to answer questions about cognitive-hq status.

---

## Cancelled Tasks

### [~] Phase 1.1–1.3: OpenClaw install, configure, test
**Cancelled:** 2026-02-06
**Reason:** Pivot to custom agent. OpenClaw dropped.

### [~] Phase 2: Secretary capabilities (OpenClaw-based)
**Cancelled:** 2026-02-06
**Reason:** Deferred. Will revisit after custom agent MVP.

### [~] Phase 3: Logging subsystem (OpenClaw-based)
**Cancelled:** 2026-02-06
**Reason:** Deferred. Will revisit after custom agent MVP.

### [~] Manual E2E Test: Real CloudCode loop (Python agent)
**Cancelled:** 2026-02-14
**Reason:** Python agent superseded by claude-telegram-relay. Python agent was per-turn invocation; relay provides superior architecture with session continuity.

### [~] Replace Telegram emulator with real bot (Python agent)
**Cancelled:** 2026-02-14
**Reason:** Python agent superseded. Real Telegram bot now working via claude-telegram-relay.

### [~] Replace memory emulator with vector DB (Python agent)
**Cancelled:** 2026-02-14
**Reason:** Python agent superseded. Semantic memory via Supabase is the path forward (pending setup).

### [~] Deploy to Google Cloud VM (Python agent)
**Cancelled:** 2026-02-14
**Reason:** Python agent superseded. Future deployment will use relay instead.

### [~] Add scheduler / proactive tasks (Python agent)
**Cancelled:** 2026-02-14
**Reason:** Python agent superseded. Relay has built-in examples for this (smart-checkin.ts, morning-briefing.ts).

### [~] Fix Python environment (.python-version)
**Cancelled:** 2026-02-14
**Reason:** No longer critical. Python agent superseded by TypeScript/Bun relay. Python env still exists but not actively used.

---

## Completed Tasks

### [x] Initialize repository structure
**Completed:** 2026-02-03
**Outcome:** Created .claude/ directory with all template files

---

### [x] Evaluate Clawdbot capabilities
**Completed:** 2026-02-04
**Outcome:** Audited and documented. Now superseded by custom agent approach.

---

### [x] Design minimal Telegram gateway v0
**Completed:** 2026-02-04
**Outcome:** Documented in GATEWAY_DESIGN_V0.md. Now superseded by custom agent approach.

---

### [x] MVP-1: Create repository skeleton
**Completed:** 2026-02-07
**Outcome:** Full folder structure, pyproject.toml, requirements.txt, .gitignore, config, state, all module stubs, prompt pack files.

---

### [x] MVP-2: Implement Memory Emulator
**Completed:** 2026-02-07
**Outcome:** `MemoryEmulator` class with JSONL backend. memory_put, memory_search (naive text match), memory_get_latest. 14 tests passing.

---

### [x] MVP-3: Implement Telegram Emulator
**Completed:** 2026-02-07
**Outcome:** `TelegramEmulator` class with inbox/outbox JSONL. `send_message.py` CLI. 16 tests passing.

---

### [x] MVP-4: Implement CloudCode Bridge
**Completed:** 2026-02-07
**Outcome:** `CloudCodeBridge` + `ExecutionPlan` Pydantic schema. Prompt assembly, CLI invocation, JSON parsing with code fence handling. 23 tests passing.

---

### [x] MVP-5: Implement Tool Registry
**Completed:** 2026-02-07
**Outcome:** `ToolRegistry` dispatches 4 tools to adapter methods. execute() and execute_all() with failure resilience. 10 tests passing.

---

### [x] MVP-6: Implement Agent Runner
**Completed:** 2026-02-07
**Outcome:** `AgentRunner` always-on loop. State persistence, session transcripts, CloudCode failure handling. `run_agent.py` CLI. 14 tests passing.

---

### [x] MVP-7: End-to-end integration tests
**Completed:** 2026-02-07
**Outcome:** 13 e2e tests covering all success criteria. Full suite: 90 tests, all passing.

---

### [x] Socket IPC: Replace file-based inbox with Unix domain sockets
**Completed:** 2026-02-08
**Outcome:** Inbound messages now flow via Unix socket (`state/agent.sock`) instead of shared JSONL file. `InboxServer` (daemon thread) feeds a `queue.Queue` that `TelegramEmulator.poll_inbox()` drains. `send_message.py` connects via socket client. 15 new tests, 105 total, all passing. Commit: `6db9eb0`.

---

### [x] Documentation: Interactive Testing Guide + Telegram Swap Guide
**Completed:** 2026-02-08
**Outcome:** Created `docs/INTERACTIVE_TESTING_GUIDE.md` (how to test agent, memory, emulator interactively) and `docs/TELEGRAM_SWAP_GUIDE.md` (how to swap emulator for real Telegram bot). Commit: `6db9eb0`.

---

### [~] Future: Multi-process architecture & IPC
**Partially addressed:** 2026-02-08
**Reason:** Unix domain sockets implemented for the inbound message path (the real cross-process boundary). Full multi-process architecture (separate memory service, multiple agents) deferred until there's a concrete need.

---

### [x] Install Bun runtime
**Completed:** 2026-02-14
**Outcome:** Bun v1.3.9 installed to `~/.bun/bin/bun`. Required for claude-telegram-relay (TypeScript runtime).

---

### [x] Deploy Telegram bot via claude-telegram-relay
**Completed:** 2026-02-14
**Outcome:**
- Cloned relay to `/home/lynnkse/cognitive-hq/claude-telegram-relay`
- Configured `.env` with bot token, user ID, Claude path, project directory
- Modified `relay.ts` to allow nested Claude sessions (CLAUDECODE env var)
- Bot deployed and running in background (PID: 1746159)
- Successfully tested: bot receives messages, calls Claude Code, returns responses
- Session continuity working via `--resume` flag
- Memory tags ([REMEMBER], [GOAL]) being generated but not persisted (needs Supabase)

---

### [x] Fixed Python environment for cognitive-hq project
**Completed:** 2026-02-14
**Outcome:** Created `cognitive-hq` virtualenv with Python 3.11.9. Installed dependencies (pydantic, pyyaml, pytest). Updated `.python-version` to point to new virtualenv. All 105 tests passing.

---

### [x] Configure Supabase for Persistent Memory
**Completed:** 2026-02-14
**Outcome:**
- Created Supabase project at https://jcwdfuusolpxnciqgstl.supabase.co
- Deployed database schema with 3 tables (messages, memory, logs)
- Enabled pgvector extension for semantic search
- Deployed 2 Edge Functions (embed, search) using OpenAI embeddings
- Configured 2 database webhooks for auto-embedding on INSERT
- Stored OpenAI API key in Supabase secrets
- Bot now has persistent memory across sessions
- Semantic search working: retrieves relevant context by meaning
- Memory tags ([REMEMBER], [GOAL], [DONE]) fully functional

---

### [x] Voice Transcription Setup
**Completed:** 2026-02-14
**Outcome:**
- Configured Groq cloud API for voice transcription
- Using whisper-large-v3-turbo model (state-of-the-art)
- Free tier: 2,000 transcriptions/day
- Bot can now transcribe Telegram voice messages to text
- Voice handling flow: voice → download → Groq API → transcribe → Claude response
- Verified with test script: `bun run test:voice` passed
- Bot restarted with voice support enabled (PID: 1898776)
- Note: Telegram bots cannot receive phone calls (API limitation)

---

## Task Lifecycle

1. **Active**: Currently being worked on
2. **Pending**: Planned but not started (may have blockers)
3. **Completed**: Done with documented outcome
4. **Deferred**: Postponed (with reason)
5. **Cancelled**: No longer relevant (with reason)

### [x] Fix bot session continuity
**Completed:** 2026-02-15
**Outcome:**
- Implemented per-user persistent session tracking
- Sessions stored in ~/.claude-relay/sessions/<user_id>.json
- No timeouts - sessions persist indefinitely like Claude Code CLI
- Claude's 200k context window auto-manages conversation history
- Bot now has true conversation continuity across messages
- Fixed spawn issues: added node prefix + CLAUDECODE: undefined
- Status: WORKING - tested and verified

---
