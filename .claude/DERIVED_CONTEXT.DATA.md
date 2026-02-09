# Derived Context Data — cognitive-hq

This file is NON-AUTHORITATIVE. See DERIVED_CONTEXT.md for rules.

---

## Repository Purpose (Updated 2026-02-08)

cognitive-hq serves two purposes:

1. **Meta-project**: Template system for managing Claude context across stateless LLM sessions
2. **Personal Command Center**: Building a custom always-on agent with CloudCode as the brain

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

## Current Phase: MVP + Socket IPC Complete — Awaiting Manual Testing

**Status:** All code implemented, 105 automated tests passing. Next: human tests with real CloudCode.

**Testing guide:** `docs/INTERACTIVE_TESTING_GUIDE.md`

**Test command:** `~/.pyenv/versions/3.11.9/bin/python3 -m pytest tests/ -v`
(`.python-version` points to Python 3.8 which is incompatible. Use 3.11.9 explicitly.)

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

## Key Files

| File | Purpose |
|------|---------|
| `src/cli/run_agent.py` | Start the agent |
| `src/cli/send_message.py` | Send a message to the agent (via socket) |
| `src/adapters/inbox_server.py` | Unix socket server (inbound messages) |
| `src/adapters/inbox_client.py` | Unix socket client (used by send_message.py) |
| `src/adapters/telegram_emulator.py` | Queue-based inbox, file-based outbox |
| `src/adapters/memory_emulator.py` | JSONL-based long-term memory |
| `src/runner/agent_runner.py` | Always-on polling loop |
| `src/runner/cloudcode_bridge.py` | Invokes Claude CLI, parses JSON plans |
| `docs/INTERACTIVE_TESTING_GUIDE.md` | How to test everything interactively |
| `docs/TELEGRAM_SWAP_GUIDE.md` | How to swap emulator for real Telegram bot |
| `.claude/INTENT/CUSTOM_AGENT_V0.md` | Authoritative design intent for the agent |
| `.claude/LOG.md` | Human decisions and reasoning |
| `.claude/TODO.md` | Task tracking |
