# Intent: CloudCode Always-On Agent v0

**Author:** Human
**Created:** 2026-02-06
**Status:** Active (supersedes CLAWDBOT_EVALUATION.md and GATEWAY_DESIGN_V0.md)
**Source:** `goals_and_architecture.txt` (repo root)

---

## Why Build Custom

OpenClaw was evaluated (see CLAWDBOT_EVALUATION.md) and found to have all required features.
However, it was dropped because:

- **Dependency overhead:** Node.js ecosystem, grammY, SQLite-vec — heavy for what we need
- **Opinionated structure:** OpenClaw's design choices don't align with our cost/control requirements
- **Budget:** We want to control exactly when and how LLM calls happen, down to the model choice per-turn
- **Modularity:** We want every component independently swappable — OpenClaw couples them

The decision: **build a minimal custom agent in Python** that does exactly what we need, nothing more.

---

## Core Design Intent

### 1. Ping-Pong Architecture (Most Important)

CloudCode is **never long-running**. It is invoked per-turn and returns a structured JSON plan.
The Agent Runner is persistent. CloudCode is disposable.

**Why:** CloudCode sessions can drop at any time. By making every invocation self-contained
(context is passed in, plan is returned), we tolerate crashes and restarts without state loss.
The agent runner holds continuity, not the LLM.

### 2. Agent Runner as Orchestrator

The runner is a simple, always-on loop:
1. Wait for inbound message
2. Gather context (message, transcript, state, tool schemas)
3. Call CloudCode
4. Execute the returned plan (tool calls, replies, state updates)
5. Persist everything
6. Go to 1

The runner is **dumb on purpose**. All intelligence lives in CloudCode's response.
The runner just executes plans faithfully.

### 3. Emulator Pattern

Every external service starts as a local emulator:
- **Telegram Emulator:** JSONL files (inbox/outbox) + CLI tool to send messages
- **Memory Emulator:** JSONL file + naive text search

Emulators share the same interface as their real counterparts.
Swapping emulator → real service should require changing only the adapter, not the runner.

**Why:** This lets us build and test the full loop locally, without API keys, bots, or cloud services.
The architecture proves itself before any external dependency is introduced.

### 4. Structured Output Only

CloudCode must return strict JSON. No prose, no markdown, no conversational filler.

```json
{
  "assistant_message": "string",
  "tool_calls": [
    {"tool_name": "...", "args": {}}
  ],
  "state_patch": {},
  "notes": "optional, for logs only"
}
```

**Why:** The runner must be able to parse and execute the plan mechanically.
Unstructured output breaks the loop.

### 5. Cost Discipline

- Default to cheapest viable model (Haiku)
- No background LLM calls — CloudCode is only invoked when there's a message to process
- No heartbeat, no polling LLM, no "thinking" loops
- Expensive models (Sonnet, Opus) only on explicit user request

**Why:** This is a personal tool. Costs must be predictable and minimal.
A sleeping agent should cost $0.

---

## Component Contracts

### Telegram Emulator

**Inbound** (`state/telegram_inbox.jsonl`):
```json
{"ts": "ISO8601", "type": "user_message", "chat_id": "string", "message_id": "uuid", "text": "string"}
```

**Outbound** (`state/telegram_outbox.jsonl`):
```json
{"ts": "ISO8601", "type": "agent_message", "chat_id": "string", "in_reply_to": "uuid", "text": "string"}
```

### Memory Emulator

**Storage:** `state/memory/memory_store.jsonl` (append-only)

```json
{"ts": "ISO8601", "id": "uuid", "text": "string", "tags": ["string"], "source": "string", "metadata": {}}
```

**API:**
- `memory_put(text, tags=[], source="conversation", metadata={})` — append a record
- `memory_search(query, k=5)` — naive text match (vector DB later)
- `memory_get_latest(n=10)` — return most recent n records

### CloudCode Bridge

**Input to CloudCode:**
- User message
- Recent transcript (last N turns)
- Current agent state
- Tool schemas (what tools are available and their args)
- Prompt pack (system_context.md, tool_contract.md, output_format.md, examples.md)

**Output from CloudCode:**
- Strict JSON plan (see schema above)

**Error handling:**
- If CloudCode fails, returns malformed JSON, or times out → log error, skip turn, wait for next message
- Never crash the runner because of a CloudCode failure

### Tool Registry

Maps tool names to adapter functions:
- `telegram_send_message` → Telegram emulator outbound
- `memory_put` → Memory emulator put
- `memory_search` → Memory emulator search
- `memory_get_latest` → Memory emulator get_latest

Validates args before dispatching. Rejects unknown tools.

---

## Folder Structure

```
cloudcode-agent/
├── docs/ARCHITECTURE.md
├── config/
│   ├── settings.local.yaml
│   └── settings.example.yaml
├── state/
│   ├── agent_state.json
│   ├── telegram_inbox.jsonl
│   ├── telegram_outbox.jsonl
│   ├── conversations/session_YYYYMMDD.jsonl
│   └── memory/
│       ├── memory_store.jsonl
│       └── memory_index.json
├── src/
│   ├── runner/
│   │   ├── agent_runner.py
│   │   ├── cloudcode_bridge.py
│   │   ├── plan_schema.py
│   │   ├── logging_utils.py
│   │   └── time_utils.py
│   ├── adapters/
│   │   ├── telegram_emulator.py
│   │   ├── memory_emulator.py
│   │   └── tool_registry.py
│   ├── cloudcode_prompts/
│   │   ├── system_context.md
│   │   ├── tool_contract.md
│   │   ├── output_format.md
│   │   └── examples.md
│   └── cli/
│       ├── run_agent.py
│       ├── send_message.py
│       └── memory_cli.py
├── tests/
│   ├── test_memory_emulator.py
│   └── test_plan_schema.py
├── requirements.txt
└── pyproject.toml
```

---

## MVP Success Criteria

If we can:
1. Start the runner (`python src/cli/run_agent.py`)
2. Send a message (`python src/cli/send_message.py "hello"`)
3. Get a reply
4. Store + retrieve memory

...then the skeleton is a success.

---

## Future Direction (Not MVP)

- Replace Telegram emulator → real Telegram bot (python-telegram-bot or grammY via bridge)
- Replace memory emulator → vector DB (ChromaDB, or SQLite-vec)
- Add Google APIs via MCP tool server
- Deploy to Google Cloud VM
- Add scheduler / proactive tasks (cron-like, within the runner)
- Secretary capabilities (reminders, task tracking, agenda)
- Logging subsystems (food, workout, work hours)

---

## Known Tradeoffs

1. **Naive text search** for memory is a placeholder. It will miss semantic matches. Acceptable for MVP.
2. **File-based message queue** (JSONL) has no locking. Fine for single-user local prototype. Must be replaced for production.
3. **Per-turn CloudCode invocation** adds latency (~2-5s per turn). Acceptable for personal assistant use case.
4. **No streaming** — the agent waits for the full CloudCode response. Streaming can be added later if needed.
5. **No authentication** — local prototype assumes trusted single user.
