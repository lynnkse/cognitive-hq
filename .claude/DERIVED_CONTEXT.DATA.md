# Derived Context Data — cognitive-hq

⚠️ This file is NON-AUTHORITATIVE. See DERIVED_CONTEXT.md for rules.

---

## Repository Purpose (Updated 2026-02-04)

cognitive-hq serves two purposes:

1. **Meta-project**: Template system for managing Claude context across stateless LLM sessions
2. **Personal Command Center**: Building a Telegram-based personal assistant using OpenClaw

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

### 2. Use OpenClaw (Clawdbot), Don't Build
- OpenClaw already has: Telegram, cron, hooks, skills, memory
- Configure and extend, don't reinvent
- OpenClaw repo cloned to: `/home/lynnkse/openclaw`

### 3. Cost Discipline
- Cheap models by default (Haiku)
- No background LLM loops (heartbeat disabled)
- Expensive models only on explicit request

### 4. Stateless by Default
- No automatic persistence
- User must say "log this", "save this", "remember this", etc.

---

## Current Phase: 1 — Clawdbot Gateway v0

**Status:** Planning complete, implementation pending

**What's done:**
- [x] Evaluated OpenClaw capabilities (CLAWDBOT_EVALUATION.md)
- [x] Designed minimal gateway (GATEWAY_DESIGN_V0.md)
- [x] Cloned OpenClaw to /home/lynnkse/openclaw

**What's next:**
- [ ] Create Telegram bot via @BotFather
- [ ] Install OpenClaw: `npm install -g openclaw`
- [ ] Configure with cost-discipline settings
- [ ] Create workspace directories and system prompt
- [ ] Test basic functionality

---

## Key Files

| File | Purpose |
|------|---------|
| MASTER_ROADMAP.md | Authoritative starting point and roadmap |
| CLAWDBOT_EVALUATION.md | OpenClaw capability audit |
| GATEWAY_DESIGN_V0.md | Minimal gateway design and setup instructions |
| LOG.md | Human decisions and reasoning |
| TODO.md | Task tracking |

---

## OpenClaw Key Features (for reference)

- **Telegram:** grammY-based, production-ready, DM + groups
- **Cron:** Persistent scheduling at `~/.openclaw/cron/jobs.json`
- **Hooks:** Event-driven automation (session-memory, command-logger)
- **Skills:** Extensible (apple-reminders, obsidian, notion, etc.)
- **Memory:** Vector embeddings with SQLite-vec (optional)
- **Config:** `~/.openclaw/config.json5`

---

## Workspace Structure (planned)

```
~/.openclaw/
├── config.json5           # Main configuration
├── cron/jobs.json         # Scheduled tasks
├── workspace/
│   ├── AGENTS.md          # System prompt
│   ├── tasks/tasks.md     # Task list
│   ├── notes/notes.md     # Saved notes
│   └── logs/
│       ├── food.jsonl
│       ├── workout.jsonl
│       └── work.jsonl
```

---

## Open Questions

1. Should we use OpenClaw's memory system for certain things, or keep everything file-based?
2. How to handle model upgrades? Via command or via message?
3. Should tasks use markdown or JSONL format?
