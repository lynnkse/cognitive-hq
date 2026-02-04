# TODO — cognitive-hq Project Tasks

This file tracks active, pending, and completed tasks for the cognitive-hq project.
It is the authoritative source for task management alongside LOG.md.

---

## Active Tasks

_No active tasks_

---

## Pending Tasks

### [ ] Phase 1.1: Install and configure OpenClaw
**Priority:** HIGH
**Created:** 2026-02-04
**Status:** Not Started
**Blocked by:** Need Telegram bot token

**Steps:**
1. Create Telegram bot via @BotFather
2. Set environment variables (TELEGRAM_BOT_TOKEN, ANTHROPIC_API_KEY)
3. Install OpenClaw globally: `npm install -g openclaw`
4. Run onboarding: `openclaw onboard`
5. Apply configuration from GATEWAY_DESIGN_V0.md

---

### [ ] Phase 1.2: Configure workspace and system prompt
**Priority:** HIGH
**Created:** 2026-02-04
**Status:** Not Started
**Blocked by:** Phase 1.1

**Steps:**
1. Create workspace directories: `mkdir -p ~/.openclaw/workspace/{tasks,notes,logs}`
2. Create AGENTS.md system prompt (from GATEWAY_DESIGN_V0.md)
3. Verify directory structure

---

### [ ] Phase 1.3: Test basic gateway functionality
**Priority:** HIGH
**Created:** 2026-02-04
**Status:** Not Started
**Blocked by:** Phase 1.2

**Success criteria:**
- [ ] Can send message to bot, get response
- [ ] Response uses cheap model (Haiku)
- [ ] "Set reminder" creates working cron job
- [ ] "Log this: ate breakfast" appends to food.jsonl
- [ ] No background LLM calls when idle
- [ ] Restart preserves cron jobs

---

### [ ] Phase 2: Secretary capabilities
**Priority:** MEDIUM
**Created:** 2026-02-04
**Status:** Not Started
**Blocked by:** Phase 1.3

**Features:**
- Natural language reminder parsing
- Task management with completion tracking
- Agenda/calendar view
- Proactive reminder delivery

---

### [ ] Phase 3: Logging subsystem
**Priority:** LOW
**Created:** 2026-02-04
**Status:** Not Started
**Blocked by:** Phase 2

**Features:**
- Food logging with nutrition summaries
- Workout logging with trends
- Work hours tracking with reports

---

## Completed Tasks

### [x] Initialize repository structure
**Completed:** 2026-02-03
**Outcome:** Created .claude/ directory with all template files

---

### [x] Evaluate Clawdbot capabilities
**Completed:** 2026-02-04
**Outcome:**
- OpenClaw (formerly Clawdbot) audited
- Cloned to /home/lynnkse/openclaw
- All required features exist (Telegram, cron, hooks, skills)
- Documented in CLAWDBOT_EVALUATION.md

---

### [x] Design minimal Telegram gateway v0
**Completed:** 2026-02-04
**Outcome:**
- Design documented in GATEWAY_DESIGN_V0.md
- Decision: use OpenClaw as-is, configure don't build
- Configuration, system prompt, and setup instructions defined

---

## Task Lifecycle

1. **Active**: Currently being worked on
2. **Pending**: Planned but not started (may have blockers)
3. **Completed**: Done with documented outcome
4. **Deferred**: Postponed (with reason)
5. **Cancelled**: No longer relevant (with reason)
