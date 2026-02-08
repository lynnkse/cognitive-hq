# Derived Context Data — cognitive-hq

This file is NON-AUTHORITATIVE. See DERIVED_CONTEXT.md for rules.

---

## Repository Purpose (Updated 2026-02-07)

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
- Telegram emulator (file/CLI) -> real Telegram bot
- Memory emulator (JSONL) -> vector DB
- Local runner -> Google Cloud VM

---

## Current Phase: MVP COMPLETE — Awaiting Manual Testing

**Status:** All code implemented, 90 automated tests passing. Next: human tests with real CloudCode.

**Architecture source:** `goals_and_architecture.txt` (repo root)

### Components (all implemented)

| Component | File(s) | Status |
|-----------|---------|--------|
| Agent Runner | `src/runner/agent_runner.py` | Done (14 tests) |
| CloudCode Bridge | `src/runner/cloudcode_bridge.py` | Done (13 tests) |
| Plan Schema | `src/runner/plan_schema.py` | Done (10 tests) |
| Telegram Emulator | `src/adapters/telegram_emulator.py` | Done (16 tests) |
| Memory Emulator | `src/adapters/memory_emulator.py` | Done (14 tests) |
| Tool Registry | `src/adapters/tool_registry.py` | Done (10 tests) |
| Prompt Pack | `src/cloudcode_prompts/` | Done |
| CLI: run_agent | `src/cli/run_agent.py` | Done |
| CLI: send_message | `src/cli/send_message.py` | Done |
| CLI: memory_cli | `src/cli/memory_cli.py` | Stub only |
| Logging | `src/runner/logging_utils.py` | Done |
| Time Utils | `src/runner/time_utils.py` | Done |
| E2E Tests | `tests/test_e2e.py` | Done (13 tests) |

### Data Flow (One Cycle)
1. User sends message via `send_message.py` -> appends to `state/telegram_inbox.jsonl`
2. Agent runner detects new inbound message
3. Agent runner prepares CloudCode input: user message + recent transcript + agent state + tool schemas
4. CloudCode returns JSON plan: `{assistant_message, tool_calls, state_patch, notes}`
5. Agent runner executes tool calls in order, sends responses, persists state
6. Loop waits for next input

### How to Run (3 terminals)

**Terminal 1 — Claude Code** (development/debugging):
```
claude
```

**Terminal 2 — Agent Runner** (always-on, waiting for messages):
```
python src/cli/run_agent.py
# Options: --model haiku --poll-interval 2 --timeout 30 --log-level INFO
```

**Terminal 3 — Send Messages** (simulates Telegram):
```
python src/cli/send_message.py "hello agent"
python src/cli/send_message.py "remember that I prefer Python"
python src/cli/send_message.py "what do you know about me?"
```

### Observing Results
- Agent replies: `state/telegram_outbox.jsonl`
- Memory entries: `state/memory/memory_store.jsonl`
- Session transcript: `state/conversations/session_YYYYMMDD.jsonl`
- Agent state: `state/agent_state.json`

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

## Resolved Questions (from MVP implementation)

| Question | Answer |
|----------|--------|
| Python version? | 3.10+ (pyenv virtualenv `anplos-video`, Python 3.12.3) |
| How to invoke CloudCode? | `claude -p <prompt> --model <model> --no-input` via subprocess |
| Async or polling? | Simple polling loop (`time.sleep`) — good enough for MVP |
| CloudCode error handling? | `CloudCodeError` exception, caught in runner, logged in transcript, loop continues |
| Config format? | YAML — `config/settings.example.yaml` has all settings |

## Remaining Open Questions

1. Will `claude -p` with a very long prompt (prompt pack + transcript) work reliably?
2. Does the agent need to handle multi-turn tool calls (e.g., search memory then reply with results)?
3. Should `memory_cli.py` be fully implemented or is it low priority?

---

## Key Files

| File | Purpose |
|------|---------|
| `goals_and_architecture.txt` | Authoritative architecture spec for custom agent |
| `src/cli/run_agent.py` | Start the agent |
| `src/cli/send_message.py` | Send a message to the agent |
| MASTER_ROADMAP.md | High-level project vision and roadmap |
| LOG.md | Human decisions and reasoning |
| TODO.md | Task tracking |
