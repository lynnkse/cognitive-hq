# TODO — cognitive-hq Project Tasks

This file tracks active, pending, and completed tasks for the cognitive-hq project.
It is the authoritative source for task management alongside LOG.md.

---

## Active Tasks

### [ ] Manual E2E Test: Real CloudCode loop
**Priority:** HIGH
**Created:** 2026-02-07
**Status:** Awaiting human testing

**Goal:** Verify the full agent loop works with real CloudCode (not mocked).

**Setup (3 terminals):**
1. **Terminal 1** — Claude Code session (for development/debugging)
2. **Terminal 2** — Start the agent:
   ```
   python src/cli/run_agent.py
   ```
3. **Terminal 3** — Send messages:
   ```
   python src/cli/send_message.py "hello agent"
   python src/cli/send_message.py "remember that I prefer Python"
   python src/cli/send_message.py "what do you know about me?"
   ```

**Verify:**
- [ ] Agent starts without errors
- [ ] Sending a message produces a reply in the terminal 2 logs
- [ ] Reply appears in `state/telegram_outbox.jsonl`
- [ ] Memory is stored in `state/memory/memory_store.jsonl`
- [ ] Memory search retrieves stored entries
- [ ] Session transcript written to `state/conversations/session_*.jsonl`
- [ ] Agent survives if CloudCode times out or errors (keeps running)
- [ ] Agent state persists in `state/agent_state.json`

**If something fails:** fix it, re-run automated tests (`python3 -m pytest tests/ -v`), retry.

---

## Pending Tasks

### [ ] Future: Replace Telegram emulator with real bot
**Priority:** LOW
**Created:** 2026-02-06
**Blocked by:** Manual E2E test

---

### [ ] Future: Replace memory emulator with vector DB
**Priority:** LOW
**Created:** 2026-02-06
**Blocked by:** Manual E2E test

---

### [ ] Future: Deploy to Google Cloud VM
**Priority:** LOW
**Created:** 2026-02-06
**Blocked by:** Manual E2E test

---

### [ ] Future: Add scheduler / proactive tasks
**Priority:** LOW
**Created:** 2026-02-06
**Blocked by:** Manual E2E test

---

### [ ] Future: Multi-process architecture & IPC
**Priority:** LOW
**Created:** 2026-02-07
**Blocked by:** Manual E2E test

**Context:** Currently everything runs in a single Python process with direct function calls. If we later need multiple independent agent processes (e.g., separate memory service, multiple agent brains, parallel tool executors), we'll need inter-process communication.

**Options to evaluate when the time comes:**
- Unix/TCP sockets (lightweight, no dependencies)
- ZeroMQ (fast, flexible patterns: pub/sub, req/rep, push/pull)
- Redis pub/sub (if we already use Redis for memory/state)
- gRPC (typed contracts, good for structured services)
- Simple HTTP/REST (universal, easy to debug)
- ROS2-style (only if robotics-adjacent or many heterogeneous nodes)

**Decision deferred** — current single-process architecture is correct for now. Revisit when there's a concrete need for multiple processes.

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

## Task Lifecycle

1. **Active**: Currently being worked on
2. **Pending**: Planned but not started (may have blockers)
3. **Completed**: Done with documented outcome
4. **Deferred**: Postponed (with reason)
5. **Cancelled**: No longer relevant (with reason)
