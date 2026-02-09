# Interactive Testing Guide

How to manually test the always-on agent, the Telegram emulator, and the memory system.

---

## Prerequisites

You need Python 3.10+ with `pydantic`, `pyyaml`, and `pytest` installed.
You need `claude` CLI available in your PATH (for the real CloudCode loop).

Check:
```bash
python3 --version          # must be 3.10+
claude --version           # must be installed
python3 -c "import pydantic, yaml"  # must not error
```

---

## 1. Run the Automated Tests First

Before doing anything interactive, verify the test suite passes:

```bash
python3 -m pytest tests/ -v
```

Expected: 105 tests, all passing. If this fails, fix the issue before proceeding.

---

## 2. Test the Agent (Full Loop)

This is the main test. You'll start the agent in one terminal and send messages from another.

### What happens under the hood

```
You type a message (Terminal 2)
    |
    v  (Unix socket)
InboxServer receives it, queues it
    |
    v
AgentRunner polls the queue, finds your message
    |
    v
CloudCodeBridge builds a prompt (your message + context + prompt pack)
    |
    v
Claude CLI is invoked, returns a JSON plan
    |
    v
AgentRunner executes the plan:
  - Sends reply via telegram_send_message (-> outbox file)
  - Stores memories via memory_put (-> memory file)
  - Updates agent state (-> state file)
    |
    v
AgentRunner waits for next message
```

### Step-by-step

**Terminal 1 — Start the agent:**

```bash
python3 src/cli/run_agent.py
```

You'll see:
```
Agent runner starting (model=haiku, poll=2.0s)
Listening for messages on state/agent.sock
Send messages with: python src/cli/send_message.py "your message"
Press Ctrl+C to stop.
```

The agent is now running and waiting. It polls the inbox queue every 2 seconds.

**Terminal 2 — Send messages:**

```bash
# Basic greeting
python3 src/cli/send_message.py "hello, who are you?"
```

You'll get an ack back immediately:
```json
{
  "status": "ok",
  "message_id": "some-uuid",
  "ts": "2026-02-08T..."
}
```

Back in Terminal 1, you should see log lines showing the agent processing your message and invoking CloudCode. After a few seconds (CloudCode latency), the agent executes the plan.

**Send more messages to test different behaviors:**

```bash
# Ask it to remember something
python3 src/cli/send_message.py "remember that my favorite language is Python"

# Ask it to recall
python3 src/cli/send_message.py "what do you know about me?"

# Ask a plain question
python3 src/cli/send_message.py "what is the capital of France?"
```

### Where to see results

After sending messages, check these files to see what happened:

**Agent's replies:**
```bash
cat state/telegram_outbox.jsonl
```
Each line is a JSON object with the agent's response. Look at the `"text"` field.

**Memory stored by the agent:**
```bash
cat state/memory/memory_store.jsonl
```
If the agent decided to store a memory (e.g., "my favorite language is Python"), you'll see it here.

**Full conversation transcript:**
```bash
cat state/conversations/session_$(date -u +%Y%m%d).jsonl
```
This shows the complete back-and-forth: your messages (`role: user`), CloudCode's plans (`role: assistant`), and tool execution results (`role: tool_results`).

**Agent state:**
```bash
cat state/agent_state.json
```
This is the persistent state that CloudCode can read and update across turns.

### Stopping the agent

Press `Ctrl+C` in Terminal 1. The agent shuts down cleanly and removes the socket file.

### If something goes wrong

- **"Agent socket not found"** when sending: The agent isn't running. Start it first.
- **CloudCode timeout or error**: Check Terminal 1 logs. The agent survives CloudCode failures — it logs the error and waits for the next message. Try sending again.
- **Empty replies / no tool calls**: CloudCode might not be returning valid JSON. Check the transcript file to see the raw response.
- **To start fresh**: Delete the state files and restart:
  ```bash
  rm -f state/telegram_inbox.jsonl state/telegram_outbox.jsonl state/agent_state.json
  rm -f state/memory/memory_store.jsonl
  rm -f state/conversations/*.jsonl
  ```

---

## 3. Test the Memory System

The memory system stores and retrieves information across conversations.

### How it works

- **memory_put**: Appends a record to `state/memory/memory_store.jsonl` with text, tags, source, and metadata
- **memory_search**: Reads all records, scores them by how many query terms appear in the text and tags, returns top k
- **memory_get_latest**: Returns the n most recent records, newest first

### Test via the agent

The simplest way is through the agent (see section 2). Send messages like:
- `"remember that I have a meeting on Tuesday at 3pm"`
- `"remember I prefer dark mode"`
- `"what do you remember about meetings?"`

Then inspect the files:
```bash
# See what was stored
cat state/memory/memory_store.jsonl | python3 -m json.tool --no-ensure-ascii

# Count entries
wc -l state/memory/memory_store.jsonl
```

### Test directly in Python (no agent needed)

Open a Python REPL:
```bash
python3
```

```python
from src.adapters.memory_emulator import MemoryEmulator

mem = MemoryEmulator()  # uses default path: state/memory/memory_store.jsonl

# Store some memories
mem.memory_put("User prefers Python over JavaScript", tags=["preference", "programming"])
mem.memory_put("User has a meeting Tuesday at 3pm", tags=["schedule", "meeting"])
mem.memory_put("User lives in Tel Aviv", tags=["location", "personal"])

# Search by text
results = mem.memory_search("Python", k=5)
for r in results:
    print(r["text"], r["tags"])

# Get latest entries
latest = mem.memory_get_latest(n=10)
for entry in latest:
    print(f"[{entry['ts']}] {entry['text']}")
```

### How search works

The search is naive text matching (not semantic/vector search):
1. Split the query into terms
2. For each memory record, count how many terms appear in the text or tags (case-insensitive)
3. Score = number of matching terms
4. Return top k, sorted by score (ties broken by recency)

This means `memory_search("Python programming")` will find records containing "Python" OR "programming", ranked by how many of those terms match.

---

## 4. Test the Telegram Emulator Directly

The Telegram emulator simulates message passing via a queue (in-process) or Unix socket (cross-process).

### In-process test (Python REPL)

```python
from src.adapters.telegram_emulator import TelegramEmulator

tg = TelegramEmulator()

# Simulate a user sending a message
msg = tg.enqueue_message("hello agent", chat_id="local-test")
print("Enqueued:", msg)

# Poll for new messages (what the agent runner does)
new = tg.poll_inbox()
print("Polled:", new)

# Poll again — should be empty (already consumed)
print("Second poll:", tg.poll_inbox())

# Simulate the agent replying
reply = tg.send_message(chat_id="local-test", text="hello user!", in_reply_to=msg["message_id"])
print("Reply:", reply)

# Check the outbox
print("Outbox:", tg.get_outbox())
```

### Cross-process test (socket)

This is what actually happens in production — `send_message.py` talks to the agent via Unix socket.

Start the agent (Terminal 1), then in Terminal 2:
```bash
# Send and observe
python3 src/cli/send_message.py "test message"

# Check the socket file exists
ls -la state/agent.sock

# Check the inbox audit log (server writes here for persistence)
cat state/telegram_inbox.jsonl

# Check the outbox (agent replies end up here)
cat state/telegram_outbox.jsonl
```

---

## 5. Test with Different Models

By default, the agent uses Haiku (cheapest). You can change the model:

```bash
# Use Sonnet (smarter, more expensive)
python3 src/cli/run_agent.py --model sonnet

# Use Opus (most capable, most expensive)
python3 src/cli/run_agent.py --model opus

# Adjust timeout for slower models
python3 src/cli/run_agent.py --model sonnet --timeout 60
```

---

## 6. Watch Everything in Real-Time

For the best visibility into what's happening, open 4 terminals:

| Terminal | Command | What you see |
|----------|---------|-------------|
| 1 | `python3 src/cli/run_agent.py --log-level DEBUG` | Agent logs (every step of processing) |
| 2 | `python3 src/cli/send_message.py "your message"` | Send messages, get acks |
| 3 | `tail -f state/telegram_outbox.jsonl` | Agent replies appear in real-time |
| 4 | `tail -f state/memory/memory_store.jsonl` | Memory entries appear in real-time |

---

## Checklist

After testing, verify these all work:

- [ ] Agent starts without errors
- [ ] Sending a message produces an ack in Terminal 2
- [ ] Agent logs show message processing in Terminal 1
- [ ] Reply appears in `state/telegram_outbox.jsonl`
- [ ] Memory is stored in `state/memory/memory_store.jsonl` (when asked to remember)
- [ ] Memory search retrieves stored entries (when asked to recall)
- [ ] Transcript is written to `state/conversations/session_*.jsonl`
- [ ] Agent survives if CloudCode times out (keeps running, processes next message)
- [ ] Agent state persists in `state/agent_state.json`
- [ ] Ctrl+C stops the agent cleanly (socket file removed)
