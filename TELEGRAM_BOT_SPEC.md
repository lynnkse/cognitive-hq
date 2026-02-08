# Telegram Gateway Bot Specification
## Clawdbot-Based Command Interface

---

## Purpose

This document defines the **design, behavior, and constraints** of the Telegram bot.

The bot is a **gateway**, not a brain.
It is the primary human interface to a larger personal command-center system.

This document is authoritative for the Telegram bot only.
Other documents may define storage, agents, MCP tools, etc.

---

## Core Role of the Telegram Bot

The Telegram bot must:

- act as a **low-cost, lightweight command interface**
- accept natural-language input from the user
- route commands to appropriate subsystems or agents
- deliver notifications and summaries back to the user
- **never** act as the primary state holder

The bot is **not responsible** for:
- long-term memory
- background reasoning
- planning loops
- task polling
- heavy computation

---

## Implementation Requirement

The bot **must be implemented using Clawdbot**.

Before writing custom code, the agent must:
1. Audit Clawdbot’s existing capabilities
2. Identify what can be reused:
   - agent routing
   - tool invocation
   - persistence hooks
   - scheduling support
   - command parsing
3. Use Clawdbot-native features wherever possible

Custom logic is allowed **only** when Clawdbot does not support the requirement.

---

## Cost Discipline (Hard Constraint)

The bot must be extremely cheap to operate.

Rules:
- Use **cheap models by default**
- Do not replay full conversation history
- Do not maintain hidden conversational state
- No background LLM loops
- No autonomous “thinking”

Expensive models may be used **only** when explicitly requested by the user.

---

## Stateless by Default

The bot is stateless unless explicitly instructed otherwise.

This means:
- Each incoming message is processed independently
- No assumptions about prior messages
- No reliance on chat history for correctness

---

## Explicit Persistence Only

State may be written **only** when the user explicitly commands it.

Examples of persistence commands:
- “log this”
- “save this”
- “remember this”
- “create task”
- “set reminder”
- “add to calendar”

If persistence occurs:
- it must be visible
- it must be written to files or database
- it must not live only in LLM context

---

## Command Interpretation Model

The bot should interpret messages into one of these categories:

1. **Ephemeral Query**
   - answer and forget
   - no persistence

2. **Persistence Command**
   - extract structured data
   - write to durable storage
   - confirm action to user

3. **Action Command**
   - trigger another subsystem
   - schedule something
   - send acknowledgment

4. **Explicit Deep Reasoning Request**
   - only here may expensive models be used
   - output must be summarized and persisted if valuable

---

## Example Interactions

### Ephemeral
User:
> “What’s the difference between belief and state?”

Bot:
- answers briefly
- no storage
- no follow-up

---

### Persistence
User:
> “Log lunch: rice, chicken, salad.”

Bot:
- parses data
- writes to nutrition log
- confirms:
  “Lunch logged.”

---

### Reminder
User:
> “Remind me tomorrow at 9am to do X.”

Bot:
- routes to secretary logic
- writes task + schedule
- confirms reminder creation

---

### Completion
User:
> “Done.”

Bot:
- resolves most recent pending task
- marks completed
- confirms

---

## Notifications

The bot may send **proactive messages** only when triggered by:
- a scheduler
- an explicit external event
- a stored reminder

The bot must **never** poll or “check” by itself using LLM calls.

---

## Tone & UX

- concise
- neutral
- non-chatty
- no emojis unless explicitly enabled
- no unnecessary follow-ups

The bot should feel like:
> a calm, reliable command terminal — not a chat companion

---

## Failure Behavior

On ambiguity:
- ask for clarification
- do not guess
- do not persist partial data

On errors:
- fail closed
- explain briefly
- do not retry autonomously

---

## Security & Privacy

- No data sent to external services without explicit intent
- No logging of sensitive data unless requested
- No cross-user assumptions (single-user system for now)

---

## Non-Goals (Explicitly Out of Scope)

The Telegram bot must NOT:
- be a general AI assistant
- maintain global conversational memory
- manage its own long-term state
- autonomously generate tasks or plans
- scrape the internet
- act without user initiation

---

## Immediate Next Step for the Coding Agent

1. Review Clawdbot documentation and features
2. Map this spec to Clawdbot primitives
3. Implement a minimal Telegram gateway:
   - receive message
   - classify intent
   - route or respond
4. Keep everything stateless by default
5. Document decisions and limitations

Start minimal.
Preserve correctness.
Optimize for durability and cost.
