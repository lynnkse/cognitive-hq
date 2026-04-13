# Relay v2 — Dev TODO

## Pending

- [ ] **GLM-Z1-32B sub-agent via MCP** — Build `glm_agent` MCP server that wraps GLM in an agentic tool loop. Claude calls `delegate_to_glm(task, context_files)`, GLM runs until done, Claude reviews and applies. Two backend options: (A) ZhipuAI API key — cheapest path, Lynn provides key; (B) local Ollama — free, needs ~20GB VRAM, one `ollama pull` command. I write all code, Lynn provides key or runs one command. Register via `claude mcp add glm-agent` automatically. **Use case: ROS/SLAM repo multi-file refactors — Claude orchestrates, GLM does heavy lifting, Claude reviews before applying.**

- [ ] **Deploy relay on work PC for ROS/SLAM repo** — Clone relay to `~/claude-relay/` on work PC (outside catkin). Set `PROJECT_DIR=/path/to/ros/repo`, `CHANNEL=work`, same Supabase credentials. Relay spawns Claude with `cwd=PROJECT_DIR` so existing `.claude/BOOTSTRAP.md` structure is picked up automatically. No changes to ROS repo needed. Same Supabase DB — `channel` column separates personal vs work.

- [ ] **`knowledge` table: professional insights across projects** — Separate table from `memory` (which stays personal). Stores lessons learned, procedures, patterns, warnings per project. Has `project` column (null = cross-project). Needs schema migration + `embed` webhook + injection into system prompt filtered by current project. Design doc needed before implementation.

- [ ] **Agentic `search_memory` tool** — Instead of injecting all memory at startup (blunt), give Claude a tool it can call when it judges relevant context exists. Works for both `memory` and `knowledge` tables. Requires exposing a search endpoint the relay can call and pass results back to Claude mid-conversation.

- [ ] **Claude Code hook: Supabase memory injection at session startup** — Build a Claude Code startup hook that queries Supabase `memory` table (facts, goals, preferences) and injects them into the session context. This closes the gap where CLI/Claude Code sessions don't benefit from long-term memory — currently only the Telegram relay gets memory injection via system prompt. Goal: unified memory across both relay and Claude Code sessions, replacing `DERIVED_CONTEXT.DATA.md` for personal/cross-session knowledge.

- [ ] **Full response delivery after multi-step tasks** — After long runs (log + commit + multiple permissions), the final text response sometimes never appears in Telegram. Either the JSONL debounce window is too short for slow multi-tool responses, or the response times out. Need to investigate: check if final text entry is written to JSONL after long tool chains, tune debounce/timeout, and ensure the complete summary response (not just tool confirmations) reaches the user.

- [ ] **Message source metadata in responses** — Claude should know whether a message came from Telegram or CLI (or which CLI user, future multi-user). The `source` field already flows through QueueItem and is published with each response; expose it to the Claude prompt so it can tailor its reply (e.g. keep responses concise for Telegram, can be verbose for CLI). Consider injecting source into the PTY message prefix: `[from:telegram] user message here`.

- [ ] **Dreaming mode / memory consolidation** — Background process that consolidates raw Supabase memory into high-signal durable knowledge. Runs when agent is idle. Three phases: light (extract candidates), REM (detect patterns, strengthen), deep (score + promote to durable memory). See `DREAMING_MODE.md` for full spec. **Prerequisite: plain Supabase memory must be working and validated first.**

- [ ] **GLM-Z1-32B sub-agent via MCP** — Build `glm_agent` MCP server that wraps GLM in an agentic tool loop. Claude calls `delegate_to_glm(task, context_files)`, GLM runs until done, Claude reviews and applies. Two backend options: (A) ZhipuAI API key — cheapest path, Lynn provides key; (B) local Ollama — free, needs ~20GB VRAM, one `ollama pull` command. I write all code, Lynn provides key or runs one command. Register via `claude mcp add glm-agent` automatically.

## Done

- [x] Permission deadlock via PermissionRequest hook (concurrent_updates fix)
- [x] JSONL-based response detection
- [x] TelegramNode inline Allow/Deny buttons for permission requests
