# Claude Telegram Relay — Architecture Reference

**Repository:** `lynnkse/claude-telegram-relay`
**Runtime:** Bun (TypeScript)
**Last updated:** 2026-02-21

---

## 1. What It Does

The relay is a Telegram bot that acts as a bridge between you and Claude Code CLI. Every message you send via Telegram is enriched with memory context, passed to Claude, and the response is returned — with memory tags automatically extracted and saved to Supabase.

---

## 2. High-Level Architecture

```
You (Telegram)
      │
      ▼
 grammY Bot
      │
      ├─ Text message
      ├─ Voice message ──► transcribe.ts ──► Groq/whisper.cpp
      ├─ Photo
      └─ Document
      │
      ▼
 buildPrompt()
  ├─ System persona + time
  ├─ User profile (config/profile.md)
  ├─ FACTS + GOALS from Supabase (getMemoryContext)
  ├─ Semantically relevant past messages (getRelevantContext)
  ├─ Memory tag instructions
  └─ Task management instructions (PROJECT_DIR/.claude/TODO.md)
      │
      ▼
 callClaude()
  ├─ node <claude-path> -p <prompt> --output-format json
  ├─ --resume <session_id>  (if session exists)
  └─ cwd: PROJECT_DIR
      │
      ▼
 Claude Code CLI
  ├─ Reads .claude/ context files (BOOTSTRAP, TODO, LOG, etc.)
  ├─ Has Read/Edit/Write tool access (settings.local.json)
  └─ Returns JSON: { result, session_id, ... }
      │
      ▼
 Parse JSON response
  ├─ Save session_id → ~/.claude-relay/sessions/<user_id>.json
  └─ Extract result text
      │
      ▼
 processMemoryIntents()  (memory.ts)
  ├─ [REMEMBER: fact]   → INSERT into Supabase memory table
  ├─ [GOAL: text]       → INSERT into Supabase memory table
  ├─ [DONE: text]       → UPDATE goal → completed_goal
  └─ Strip all tags from response text
      │
      ▼
 saveMessage()          → INSERT into Supabase messages table
      │
      ▼
 sendResponse()         → Telegram reply (chunked if > 4000 chars)
```

---

## 3. File Structure

```
claude-telegram-relay/
├── src/
│   ├── relay.ts        — Main bot (entry point, all orchestration)
│   ├── memory.ts       — Supabase memory read/write
│   └── transcribe.ts   — Voice transcription (Groq or local whisper)
├── config/
│   └── profile.md      — User profile injected into every prompt
├── .env                — Runtime configuration (gitignored)
├── .env.example        — Configuration template
└── daemon/
    └── claude-relay.service  — systemd unit file template
```

---

## 4. Module Breakdown

### 4.1 `relay.ts` — Core Orchestrator

**Configuration (top of file)**

| Variable | Env var | Purpose |
|----------|---------|---------|
| `BOT_TOKEN` | `TELEGRAM_BOT_TOKEN` | Telegram bot authentication |
| `ALLOWED_USER_ID` | `TELEGRAM_USER_ID` | Security — only this user can use the bot |
| `CLAUDE_PATH` | `CLAUDE_PATH` | Path to Claude Code CLI binary |
| `PROJECT_DIR` | `PROJECT_DIR` | Working directory for Claude (your repo) |
| `RELAY_DIR` | `RELAY_DIR` | Where relay stores sessions/uploads (default: `~/.claude-relay`) |
| `CHANNEL` | `CHANNEL` | Tags messages in Supabase by machine (`personal`/`work`) |

---

**Session Management**

Session continuity is the mechanism that makes Claude remember the conversation across messages. Without it, every message starts a fresh Claude session with no prior context.

```
getUserSession(userId)
  └─ Reads ~/.claude-relay/sessions/<user_id>.json
  └─ Returns saved session_id or null

saveUserSession(userId, sessionId)
  └─ Writes session_id to ~/.claude-relay/sessions/<user_id>.json

findLatestSession()  ← DEPRECATED (unreliable, kept for reference)
  └─ Was scanning ~/.claude/projects/<path>/ for newest .jsonl
  └─ Failed because Claude hashes the project path, not encodes it
```

Session flow per message:
1. `getUserSession()` → get saved `session_id`
2. Pass `--resume <session_id>` to Claude CLI
3. Claude CLI returns JSON with new `session_id`
4. `saveUserSession()` → persist new `session_id`
5. Next message resumes from where this one ended

---

**`callClaude(prompt, userId, options)`**

The core function that invokes Claude Code CLI.

```typescript
args = ["node", CLAUDE_PATH, "-p", prompt]
args += ["--resume", sessionId]      // if session exists
args += ["--output-format", "json"]  // get structured response + session_id
```

Runs Claude with:
- `cwd: PROJECT_DIR` — Claude sees your repo as its working directory
- `CLAUDECODE: undefined` — allows nested Claude sessions (prevents env conflict)

Returns `parsed.result` (the text response) and saves `parsed.session_id`.

---

**`buildPrompt(userMessage, relevantContext, memoryContext)`**

Assembles the full prompt sent to Claude. Parts added in order:

1. **System persona** — "You are a personal AI assistant via Telegram..."
2. **User name** — from `USER_NAME` env var
3. **Current time** — formatted in user's timezone (`USER_TIMEZONE`)
4. **Profile** — contents of `config/profile.md` (if exists)
5. **Memory context** — FACTS + GOALS from Supabase
6. **Relevant context** — semantically similar past messages (semantic search)
7. **Memory tag instructions** — tells Claude how to use `[REMEMBER]`, `[GOAL]`, `[DONE]`
8. **Task management instructions** — tells Claude it can read/edit `PROJECT_DIR/.claude/TODO.md`
9. **User message** — the actual message from Telegram

---

**Message Handlers**

| Handler | Trigger | Extra processing |
|---------|---------|-----------------|
| `message:text` | Text message | Direct |
| `message:voice` | Voice message | Download → `transcribe()` → treat as text |
| `message:photo` | Image | Download to `~/.claude-relay/uploads/`, pass path to Claude |
| `message:document` | File | Download to uploads, pass path to Claude |

All handlers follow the same pipeline: enrich → Claude → memory → save → reply.

---

**Lock File**

`~/.claude-relay/bot.lock` stores the running PID. On startup, if a lock exists and the PID is alive, the bot refuses to start (prevents duplicate instances). Stale locks (dead PID) are overwritten.

---

### 4.2 `memory.ts` — Supabase Memory

**Three Supabase tables used:**

| Table | Purpose |
|-------|---------|
| `messages` | Full conversation history (role, content, channel, metadata) |
| `memory` | Extracted facts and goals (type, content, deadline) |
| *(embeddings)* | Auto-generated by Supabase Edge Function `embed` on INSERT |

**`processMemoryIntents(supabase, response)`**

Scans Claude's raw response for memory tags using regex:

| Tag | Action |
|-----|--------|
| `[REMEMBER: fact]` | INSERT into `memory` with `type: "fact"` |
| `[GOAL: text \| DEADLINE: date]` | INSERT into `memory` with `type: "goal"` |
| `[DONE: search text]` | Finds matching goal by content, UPDATE to `type: "completed_goal"` |

All tags are stripped from the response before it's shown to you.

**`getMemoryContext(supabase)`**

Calls two Supabase RPC functions:
- `get_facts` — returns all facts from the memory table
- `get_active_goals` — returns all non-completed goals

Result is injected into every prompt as a `FACTS:` / `GOALS:` block.

**`getRelevantContext(supabase, query)`**

Invokes the Supabase `search` Edge Function with the current user message as the query. The Edge Function:
1. Generates an OpenAI embedding for the query (OpenAI key stays in Supabase, never in your `.env`)
2. Runs pgvector cosine similarity search against stored message embeddings
3. Returns top 5 most semantically relevant past messages

Result is injected into the prompt as `RELEVANT PAST MESSAGES:`.

---

### 4.3 `transcribe.ts` — Voice Transcription

Routes to one of two backends based on `VOICE_PROVIDER` env var:

**Groq (cloud, current setup)**
- Model: `whisper-large-v3-turbo`
- Sends raw OGG audio buffer directly to Groq API
- Free tier: 2,000 transcriptions/day
- API key: `GROQ_API_KEY`

**Local (whisper.cpp)**
- Requires: `ffmpeg` + `whisper.cpp` binary + model file
- Pipeline: OGG → ffmpeg → WAV (16kHz mono) → whisper.cpp → text file → read
- Temp files written to `/tmp/`, cleaned up after each transcription
- Configured via: `WHISPER_BINARY`, `WHISPER_MODEL_PATH`

---

## 5. Data Flow Detail — One Message Cycle

```
1. Telegram delivers message to grammY
2. Security middleware checks user ID → reject if not ALLOWED_USER_ID
3. Handler downloads media if needed (voice/photo/document)
4. transcribe() called for voice → returns text
5. getRelevantContext() + getMemoryContext() called in parallel
6. buildPrompt() assembles full context string
7. callClaude():
   a. getUserSession() → load session_id
   b. spawn: node claude -p <prompt> --resume <id> --output-format json
   c. Wait for exit
   d. JSON.parse(stdout) → { result, session_id }
   e. saveUserSession() → persist session_id
8. processMemoryIntents() → parse tags, write to Supabase, strip tags
9. saveMessage() → INSERT full conversation turn to messages table
10. sendResponse() → reply to Telegram (chunked if needed)
```

---

## 6. Multi-Machine Setup

Two bots, one Supabase database. Messages are tagged by machine via `CHANNEL`.

| Setting | Home machine | Work machine |
|---------|-------------|-------------|
| `TELEGRAM_BOT_TOKEN` | Personal bot token | Work bot token (different) |
| `PROJECT_DIR` | `/home/lynnkse/cognitive-hq` | `/home/anton/catkin_ws/src/anplos` |
| `CHANNEL` | `personal` | `work` |
| `SUPABASE_URL` | Same | Same |
| `SUPABASE_ANON_KEY` | Same | Same |
| `CLAUDE_PATH` | `/home/lynnkse/.npm-global/bin/claude` | `/home/anton/.npm-global/bin/claude` |

Semantic search via `getRelevantContext()` searches across **all channels** — so asking the work bot about something discussed with the personal bot will find it automatically.

---

## 7. Claude Code Permissions

Claude Code's permission system (`PROJECT_DIR/.claude/settings.local.json`) controls what tools the bot's Claude invocations can use:

```json
{
  "permissions": {
    "allow": ["Read", "Edit", "Write", "Bash(git add:*)", ...]
  }
}
```

The bot's Claude can:
- **Read** any file in the project
- **Edit** and **Write** files (used for TODO.md updates)
- **Bash** — restricted to specific safe commands

---

## 8. systemd Service

Both machines run the bot as a systemd service for always-on operation:

```
sudo systemctl start claude-relay    # start
sudo systemctl stop claude-relay     # stop
sudo systemctl restart claude-relay  # restart (required after .env or relay.ts changes)
sudo systemctl status claude-relay   # check status
journalctl -u claude-relay -f        # live logs
```

Service file: `/etc/systemd/system/claude-relay.service`
Logs: systemd journal (use `journalctl`)

---

## 9. Key Design Decisions

**Why Bun?**
Fast startup, native TypeScript, compatible with Node modules. The relay spawns Claude as a subprocess using `node` explicitly (not Bun) because the Claude CLI shebang isn't handled well by Bun's spawner.

**Why `--output-format json`?**
Claude CLI returns `session_id` in the JSON response directly. Earlier approach scanned `~/.claude/projects/` for session files, but Claude hashes the project path for directory names — making filesystem scanning unreliable.

**Why per-user session files?**
Sessions are stored in `~/.claude-relay/sessions/<user_id>.json` rather than a single shared file. This supports multiple authorized users in the future without session conflicts.

**Why Supabase Edge Functions for embeddings?**
The OpenAI API key for generating embeddings lives inside Supabase (as a secret), never in your `.env`. The Edge Functions auto-embed new rows on INSERT via database webhooks, and the `search` function handles similarity queries — all without exposing the key client-side.
