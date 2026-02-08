# STATE — Git Commits

<!-- This file is auto-populated with git commits -->

---

## Current State (2026-02-07)

**Branch:** master
**Uncommitted files:**
- Full MVP implementation (src/, tests/, config/, state/, docs/)
- AGENT_RECREATION_GUIDE.md (untracked - original)
- CLAUDE.md (updated)
- .claude/ directory (updated)
- goals_and_architecture.txt (architecture spec)
- .gitignore (new)
- pyproject.toml, requirements.txt (new)

**External resources:**
- `/home/lynnkse/openclaw` — OpenClaw clone, NO LONGER NEEDED (pivot 2026-02-06)

**Active direction:** Custom always-on agent (Python) — MVP COMPLETE, awaiting manual testing

**Test suite:** 90 tests, all passing

---

## File Structure Changes

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
│   ├── telegram_emulator.py — inbox/outbox JSONL file-based messaging
│   ├── memory_emulator.py   — JSONL long-term storage (put/search/get_latest)
│   └── tool_registry.py     — dispatches tool calls to adapters
├── cloudcode_prompts/
│   ├── system_context.md
│   ├── tool_contract.md
│   ├── output_format.md
│   └── examples.md
└── cli/
    ├── run_agent.py          — entry point: start the agent
    ├── send_message.py       — CLI: enqueue a message
    └── memory_cli.py         — CLI: interact with memory (stub)

tests/
├── test_memory_emulator.py   (14 tests)
├── test_telegram_emulator.py (16 tests)
├── test_plan_schema.py       (10 tests)
├── test_cloudcode_bridge.py  (13 tests)
├── test_tool_registry.py     (10 tests)
├── test_agent_runner.py      (14 tests)
└── test_e2e.py               (13 tests)

config/
├── settings.example.yaml
└── settings.local.yaml (gitignored)

state/  (runtime data, gitignored except .gitkeep)
├── agent_state.json
├── telegram_inbox.jsonl
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
