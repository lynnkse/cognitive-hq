# Telegram Gateway v0 — Design

**Date:** 2026-02-04
**Status:** Draft
**Based on:** MASTER_ROADMAP.md, CLAWDBOT_EVALUATION.md

---

## Design Philosophy

**Use OpenClaw as-is. Configure, don't build.**

The MASTER_ROADMAP requires auditing Clawdbot before writing custom code. The audit is complete: OpenClaw has everything we need. Our job is to configure it correctly and add only the minimal glue code for explicit persistence commands.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User (Telegram)                       │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   OpenClaw Gateway                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │  Telegram   │  │    Agent    │  │    Cron     │     │
│  │  Channel    │→ │   (Haiku)   │→ │  Scheduler  │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
│         │                │                │             │
│         ▼                ▼                ▼             │
│  ┌─────────────────────────────────────────────────┐   │
│  │              ~/.openclaw/                        │   │
│  │  ├── config.json5      (configuration)          │   │
│  │  ├── cron/jobs.json    (scheduled tasks)        │   │
│  │  └── workspace/        (persisted files)        │   │
│  │      ├── logs/         (food, workouts, work)   │   │
│  │      ├── tasks/        (task management)        │   │
│  │      └── notes/        (saved thoughts)         │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## Configuration

### File: `~/.openclaw/config.json5`

```json5
{
  // Cost discipline: cheap model by default
  agents: {
    defaults: {
      model: "anthropic/claude-3-5-haiku-latest",
      maxTokens: 4096,
    }
  },

  // No background LLM loops
  heartbeat: {
    enabled: false,
  },

  // Telegram channel
  channels: {
    telegram: {
      enabled: true,
      botToken: "${TELEGRAM_BOT_TOKEN}",  // from environment
      dmPolicy: "pairing",                // require pairing for new users
      // Optional: restrict to specific user
      // allowFrom: ["123456789"],
    }
  },

  // Cron enabled for reminders
  cron: {
    enabled: true,
  },

  // Memory disabled by default (stateless)
  memory: {
    enabled: false,
  },

  // Logging for observability
  logging: {
    level: "info",
  },
}
```

### Environment Variables

```bash
# Required
export TELEGRAM_BOT_TOKEN="your-bot-token"

# Required for LLM
export ANTHROPIC_API_KEY="your-api-key"

# Optional: for explicit model upgrade requests
export OPENAI_API_KEY="your-openai-key"
```

---

## Explicit Persistence Commands

The system is stateless by default. Persistence happens only when the user explicitly requests it.

### Command Mapping

| User Says | Action |
|-----------|--------|
| "log this" / "save this" | Append to workspace log file |
| "remember this" | Save to workspace notes |
| "create task" / "add task" | Write to tasks file |
| "set reminder" / "remind me" | Create cron job |
| "add to calendar" | (Future: calendar integration) |

### Implementation Options

**Option A: System Prompt Instructions (Simplest)**

Add instructions to the system prompt telling the agent to use tools/cron when it detects these phrases:

```
When the user says "remind me" or "set reminder", use the cron.add tool to create a scheduled reminder.
When the user says "log this" or "save this", write to a file in the workspace.
```

**Option B: Custom Skill (More Control)**

Create a `secretary` skill at `~/.openclaw/skills/secretary/`:

```
secretary/
├── SKILL.md       # Skill metadata
└── tools.md       # Tool definitions
```

**Recommendation:** Start with Option A (system prompt). Add a skill later if needed.

---

## System Prompt

### File: `~/.openclaw/workspace/AGENTS.md`

```markdown
# Personal Command Center Agent

You are a personal assistant accessed via Telegram.

## Behavior Rules

1. **Stateless by default**: Do not remember anything unless explicitly asked.
2. **Cost discipline**: Be concise. Avoid lengthy responses.
3. **Explicit persistence only**: Only save/log/remember when the user says:
   - "log this" / "save this"
   - "remember this"
   - "create task" / "add task"
   - "set reminder" / "remind me"

## Persistence Actions

When asked to persist something:

### Reminders
Use the cron tool to create a scheduled reminder:
- Parse the time from the user's message
- Create a one-shot cron job with `deleteAfterRun: true`
- Deliver back to this Telegram chat

### Tasks
Append to `~/.openclaw/workspace/tasks/tasks.md`:
```
### YYYY-MM-DD HH:MM
- [ ] Task description
```

### Notes
Append to `~/.openclaw/workspace/notes/notes.md` with timestamp.

### Logs
- Food: `~/.openclaw/workspace/logs/food.jsonl`
- Workout: `~/.openclaw/workspace/logs/workout.jsonl`
- Work: `~/.openclaw/workspace/logs/work.jsonl`

Format: JSON lines with timestamp and content.

## Response Style

- Be brief and direct
- No emoji unless the user uses them
- No unnecessary pleasantries
- If something is logged/saved, confirm with one line
```

---

## Directory Structure

```
~/.openclaw/
├── config.json5           # Main configuration
├── cron/
│   └── jobs.json          # Scheduled tasks (auto-managed)
├── workspace/
│   ├── AGENTS.md          # System prompt
│   ├── tasks/
│   │   └── tasks.md       # Task list
│   ├── notes/
│   │   └── notes.md       # Saved notes
│   └── logs/
│       ├── food.jsonl     # Food log
│       ├── workout.jsonl  # Workout log
│       └── work.jsonl     # Work hours log
└── logs/
    └── commands.log       # Command audit trail (via hook)
```

---

## Setup Instructions

### 1. Install OpenClaw

```bash
# Install globally
npm install -g openclaw

# Or use pnpm
pnpm add -g openclaw
```

### 2. Create Telegram Bot

1. Message @BotFather on Telegram
2. Send `/newbot`
3. Follow prompts to create bot
4. Copy the token

### 3. Set Environment Variables

```bash
export TELEGRAM_BOT_TOKEN="123:abc..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 4. Run Onboarding

```bash
openclaw onboard
```

### 5. Apply Configuration

Copy the configuration from this document to `~/.openclaw/config.json5`.

### 6. Create Workspace Directories

```bash
mkdir -p ~/.openclaw/workspace/{tasks,notes,logs}
```

### 7. Create System Prompt

Copy the system prompt from this document to `~/.openclaw/workspace/AGENTS.md`.

### 8. Start Gateway

```bash
openclaw gateway run
```

### 9. Test

1. Open Telegram
2. Find your bot
3. Send a message
4. Complete pairing if required

---

## Cost Monitoring

To monitor token usage:

1. Enable the `model-usage` skill (if available)
2. Check Anthropic console for usage
3. Periodically review `~/.openclaw/logs/` for patterns

---

## Upgrade Path

### To use a better model temporarily:

Via Telegram command: `/model opus` (if commands enabled)

Via message: "Use opus for this: [complex question]"

The system prompt should instruct the agent to recognize model upgrade requests.

---

## What's NOT in v0

- Calendar integration (Phase 2+)
- Email/Slack ingestion (Phase 4)
- Content pipelines (Phase 4)
- Multi-user support
- Web UI

---

## Success Criteria

v0 is complete when:

1. [ ] Can send message to bot, get response
2. [ ] Response uses cheap model (Haiku)
3. [ ] "Set reminder for tomorrow at 9am to do X" creates a working cron job
4. [ ] "Log this: ate breakfast" appends to food.jsonl
5. [ ] No background LLM calls when idle
6. [ ] Restart preserves cron jobs
