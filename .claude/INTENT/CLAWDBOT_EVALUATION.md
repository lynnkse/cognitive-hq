# OpenClaw (formerly Clawdbot) Evaluation

**Date:** 2026-02-04
**Purpose:** Evaluate OpenClaw for use as the Telegram gateway in the Personal Command Center

---

## Summary

OpenClaw is a mature, feature-rich AI gateway that **exceeds our requirements**. Most of what we need already exists. The challenge is configuration and restraint, not building.

---

## Key Findings

### What Already Exists

| Requirement | OpenClaw Feature | Status |
|-------------|------------------|--------|
| Telegram bot | grammY-based Bot API integration | Production-ready |
| Agent routing | Multi-agent workspaces, session isolation | Built-in |
| Tool invocation | Extensive tool framework | Built-in |
| Scheduling | Cron system (`~/.openclaw/cron/jobs.json`) | Built-in |
| Persistence hooks | Hooks system (session-memory, command-logger) | Built-in |
| Command parsing | Native + custom Telegram commands | Built-in |
| Memory/embeddings | Vector memory with SQLite-vec | Built-in |
| Reminders | apple-reminders skill (macOS), cron jobs | Partial |

### Repository Location

Cloned to: `/home/lynnkse/openclaw`
- GitHub: https://github.com/openclaw/openclaw
- Docs: https://docs.openclaw.ai/

### Technology Stack

- **Runtime:** Node 22+, TypeScript (ESM)
- **Package manager:** pnpm
- **Telegram:** grammY (long-polling or webhook)
- **Database:** SQLite-vec for memory/embeddings
- **Scheduling:** croner library
- **Build:** tsdown, vitest for tests

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                     OpenClaw Gateway                     │
├─────────────────────────────────────────────────────────┤
│  Channels          │  Core           │  Storage          │
│  ├── Telegram      │  ├── Agents     │  ├── ~/.openclaw/ │
│  ├── WhatsApp      │  ├── Sessions   │  │   ├── config   │
│  ├── Discord       │  ├── Routing    │  │   ├── cron/    │
│  ├── Slack         │  ├── Tools      │  │   ├── memory/  │
│  └── ...           │  └── Hooks      │  │   └── logs/    │
└─────────────────────────────────────────────────────────┘
```

### Key Directories

- `~/.openclaw/` - User data directory
- `~/.openclaw/config.json5` - Main configuration
- `~/.openclaw/cron/jobs.json` - Persisted cron jobs
- `~/.openclaw/memory/` - Vector memory storage
- `~/.openclaw/workspace/` - Agent workspace files
- `~/.openclaw/hooks/` - Custom hooks

---

## Relevant Features for Personal Command Center

### 1. Cron/Scheduling System

**Location:** `src/cron/`
**Docs:** `docs/automation/cron-jobs.md`

OpenClaw has a full cron system that:
- Persists jobs to `~/.openclaw/cron/jobs.json`
- Supports one-shot (at), recurring (every), and cron expressions
- Can wake the agent immediately or on next heartbeat
- Can deliver output to any channel (Telegram, WhatsApp, etc.)

**Example CLI:**
```bash
# One-shot reminder
openclaw cron add \
  --name "Reminder" \
  --at "2026-02-05T09:00:00Z" \
  --session main \
  --system-event "Reminder: do X" \
  --wake now \
  --delete-after-run

# Recurring job
openclaw cron add \
  --name "Morning brief" \
  --cron "0 7 * * *" \
  --tz "Asia/Jerusalem" \
  --session isolated \
  --message "Summarize today's agenda." \
  --deliver \
  --channel telegram \
  --to "123456789"
```

### 2. Hooks System

**Location:** `src/hooks/`
**Docs:** `docs/hooks.md`

Bundled hooks:
- `session-memory` - Saves session context when `/new` is issued
- `command-logger` - Logs all commands to `~/.openclaw/logs/commands.log`
- `boot-md` - Runs `BOOT.md` when gateway starts

Custom hooks can be added to `~/.openclaw/hooks/`.

### 3. Skills System

**Location:** `skills/`

Existing skills that may be useful:
- `apple-reminders` - macOS Reminders integration
- `things-mac` - Things 3 task manager
- `obsidian` - Obsidian notes
- `notion` - Notion integration
- `trello` - Trello boards
- `model-usage` - Track LLM token usage
- `weather` - Weather lookups

### 4. Memory System

**Location:** `src/memory/`
**Docs:** `docs/concepts/memory.md`

Vector memory with:
- Embeddings (OpenAI, Gemini)
- SQLite-vec for storage
- Session file sync
- Search and retrieval

### 5. Telegram Channel

**Location:** `src/telegram/`, `extensions/telegram/`
**Docs:** `docs/channels/telegram.md`

Features:
- DM and group support
- Forum topics
- Custom commands (menu entries)
- Inline buttons
- Stickers
- Draft streaming
- Reaction notifications

---

## Gap Analysis

| Roadmap Requirement | Gap | Solution |
|---------------------|-----|----------|
| Stateless by default | OpenClaw has memory/sessions | Configure `session-memory` hook to only save on explicit command |
| Cheap models by default | Need to configure | Set `agents.defaults.model` to a cheap model |
| Explicit persistence | Need custom commands | Add custom commands or skill for "log this", "save this", etc. |
| Secretary tasks | Partial (cron exists) | Build a simple secretary skill using cron |
| No background LLM loops | Need to disable heartbeat | Set `heartbeat.enabled: false` or long interval |
| Cost discipline | No built-in tracking | Use `model-usage` skill or custom tracking |

---

## Recommended Approach

### Phase 1: Minimal Gateway (use what exists)

1. **Install OpenClaw globally:**
   ```bash
   npm install -g openclaw
   ```

2. **Run onboarding:**
   ```bash
   openclaw onboard
   ```

3. **Configure for cost discipline:**
   ```json5
   {
     agents: {
       defaults: {
         model: "anthropic/claude-3-5-haiku-latest",  // cheap by default
       }
     },
     heartbeat: {
       enabled: false,  // no background thinking
     },
     channels: {
       telegram: {
         enabled: true,
         dmPolicy: "pairing",
       }
     }
   }
   ```

4. **Add explicit persistence commands** via custom Telegram commands or a simple skill.

### Phase 2: Secretary Capabilities

Use the existing cron system for reminders:
- "Remind me tomorrow at 9am" → `openclaw cron add --at "..." --session main --system-event "Reminder: ..."`
- Build a simple skill that wraps cron for natural language reminder parsing

### Phase 3: Logging

Build a simple logging skill that writes to files:
- Food log → `~/.openclaw/workspace/logs/food.jsonl`
- Workout log → `~/.openclaw/workspace/logs/workouts.jsonl`
- Work hours → `~/.openclaw/workspace/logs/work.jsonl`

---

## What NOT to Build

- **Do not build a custom Telegram bot** - OpenClaw's Telegram support is production-ready
- **Do not build a custom scheduler** - Cron system already exists
- **Do not build memory from scratch** - Memory system exists
- **Do not build session management** - Already handled

---

## Next Steps

1. Install and configure OpenClaw with minimal settings
2. Create a `secretary` skill for task/reminder management
3. Create a `logging` skill for food/workout/work tracking
4. Document explicit persistence commands
5. Test cost discipline by monitoring token usage

---

## Sources

- [OpenClaw GitHub](https://github.com/openclaw/openclaw)
- [OpenClaw Docs](https://docs.openclaw.ai/)
- [Cron Jobs Documentation](https://docs.openclaw.ai/automation/cron-jobs)
- [Telegram Channel Documentation](https://docs.openclaw.ai/channels/telegram)
- [Hooks Documentation](https://docs.openclaw.ai/hooks)
