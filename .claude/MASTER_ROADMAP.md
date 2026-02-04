# Personal Command Center System
## Authoritative Starting Point & Roadmap

---

## Purpose of This Document

This document is an **authoritative starting point and roadmap** for building a personal command-center system.

It defines:
- core principles
- architectural direction
- non-negotiable constraints
- an initial phased plan

It is **not** the only document that will ever exist.
Additional specifications, subsystem designs, and decision logs are expected to be created later.

However:
- no later document may silently contradict this one
- deviations must be explicitly documented and justified

---

## High-Level Vision

Build a **personal command center** that supports and automates:

- research & engineering projects (e.g. robotics, AI, infrastructure)
- business and monetization ideas
- content creation pipelines (script → video → posting → stats)
- personal tracking (food, workouts, work hours)
- administrative / secretary tasks (reminders, agenda, follow-ups)
- communication aggregation (email, Slack, messaging)
- future automation and agent collaboration

The system should:
- grow organically
- preserve knowledge across sessions and machines
- survive model changes and restarts
- minimize manual bookkeeping
- strictly control LLM cost

---

## Fundamental Principle (NON-NEGOTIABLE)

### **LLM context is NOT memory**

- Context window = volatile RAM
- Files + databases = durable state

Any insight, plan, decision, or structured information that matters **must be persisted explicitly**.

The system must remain usable even if:
- the model forgets everything
- the session restarts
- the model is replaced
- the execution environment changes

---

## Core Architectural Idea

The system consists of:

1. **Telegram bot as a lightweight gateway (Clawdbot-based)**
2. **Durable storage (files + database)**
3. **Logical agents / subsystems**
4. **Schedulers and triggers**
5. **Optional controlled execution tools (MCP-style)**

The Telegram bot is the *interface*, not the brain.

---

## Telegram Bot: Clawdbot Gateway

The Telegram bot **must be built on Clawdbot**.

Before implementing anything custom, the agent must:
- audit Clawdbot’s existing features
- identify what already exists:
  - agent routing
  - tool invocation
  - persistence hooks
  - scheduling
  - command parsing
- reuse Clawdbot functionality wherever possible

Custom code is allowed **only** where Clawdbot cannot reasonably support the requirement.

---

## Cost Discipline (Critical)

LLM usage must be economically disciplined.

Rules:
- cheap models by default
- expensive models only on explicit request
- no automatic escalation
- no large system prompts by default
- no background “thinking loops”
- no full conversation replay unless requested

Token usage must be observable and intentional.

---

## Stateless by Default

The bot behaves as **stateless** unless explicitly instructed otherwise.

State is written **only** when the user says things like:
- “log this”
- “save this”
- “remember this”
- “create task”
- “set reminder”
- “add to calendar”

All persistence must be explicit and visible.

---

## Conceptual Agents / Subsystems

These are **logical roles**, not necessarily separate processes.
Some may already exist in Clawdbot.

### Core / Strategist Logic
- high-level planning
- synthesis of ideas
- invoked explicitly
- outputs must be written to durable storage

### Secretary Logic
- tasks
- reminders
- agenda
- calendar integration
- proactive reminders driven by schedulers (not LLM polling)

### Logging Logic
- food → nutrition summaries
- workouts → sessions & trends
- work time → clean hours & reports

### Content Pipeline Logic
- scripts
- video generation
- posting
- metrics ingestion

### Communication Ingestion (Later)
- email / Slack / messages
- summarization
- action extraction

---

## Example Reminder Workflow

User:
> “Remind me tomorrow at 9am to do X.”

System:
1. Telegram (Clawdbot) receives message
2. Routes to secretary logic
3. Writes durable state (task + schedule)
4. Scheduler triggers reminder
5. Telegram sends notification

If not acknowledged:
- reminder repeats at defined intervals

If completed:
- task marked done
- reminders stop
- completion logged

---

## Storage Strategy

### Files (Human-Readable)
Used for:
- plans
- architecture notes
- decisions
- summaries
- evolving strategy

### Database (Structured State)
Used for:
- tasks
- reminders
- schedules
- logs (food, workouts, work)
- statistics

SQLite is acceptable initially.
Design must allow migration later.

---

## Repository Philosophy

This repository is **alive**.

Rules:
- every meaningful session produces artifacts
- files override chat memory
- no undocumented mental state
- prefer explicit notes over implicit assumptions

---

## Development Roadmap (Intent)

### Phase 0 — Foundation
- persistent documents
- stop losing progress

### Phase 1 — Clawdbot Gateway v0 (**NEXT STEP**)
- Telegram bot via Clawdbot
- stateless by default
- explicit persistence commands
- cheap model usage

### Phase 2 — Secretary Capabilities
- tasks
- reminders
- calendar
- scheduler-driven notifications

### Phase 3 — Logging
- food
- workouts
- work hours
- basic reporting

### Phase 4 — Automation
- controlled execution (MCP-style)
- content pipelines
- system integrations

---

## Hard Constraints

- no hidden state in LLM context
- no reliance on chat history
- no background LLM loops
- no uncontrolled token growth
- no silent automation
- no implicit persistence

If something persists:
→ it must exist in files or database.

---

## Immediate Instruction to the Coding Agent

**Your next concrete task:**

1. Evaluate Clawdbot’s current capabilities
2. Design a minimal Telegram gateway using Clawdbot
3. Keep it stateless by default
4. Define explicit persistence commands
5. Produce files, not just code

Do not over-engineer.
Start small.
Preserve everything that matters.
