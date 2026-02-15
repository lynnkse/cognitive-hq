# Core Abstractions (cognitive-hq)

This file defines terms used in logs and discussions.

---

## Terms

### Meta-Project Terms

- **Canonical file**: A file that is authoritative source of truth (LOG.md, STATE.md, code)
- **Derived context**: Claude's cached understanding; non-authoritative and disposable
- **Promotion**: Moving information from derived context to a canonical file
- **Bootstrap**: The entry point file that lists mandatory reads for Claude sessions
- **Intent file**: Human-authored explanation of design goals and motivations
- **Stateless workflow**: Operating without relying on chat memory; all context from files
- **CLAUDE.md**: Instructions file telling Claude Code how to work with the code (static, operational)
- **.claude/ directory**: Project memory and state (dynamic, historical - decisions, tasks, logs)
- **Hierarchical context**: Multi-level CLAUDE.md files at different directory depths for scoped guidance

### Bot & Memory System Terms

- **Relay**: The claude-telegram-relay bot that bridges Telegram ↔ Claude Code
- **Session continuity**: Using `--resume` flag to maintain conversation context across Claude Code calls
- **Memory tag**: Special syntax Claude uses to mark facts/goals: `[REMEMBER: ...]`, `[GOAL: ... | DEADLINE: ...]`, `[DONE: ...]`
- **Semantic search**: Vector-based similarity search using embeddings (finds meaning, not keywords)
- **Embedding**: 1536-dimension vector representation of text (via OpenAI text-embedding-3-small)
- **Channel**: Category field in messages table for organizing contexts (personal, work, telegram)
- **pgvector**: PostgreSQL extension that enables vector similarity search
- **Edge Function**: Serverless function in Supabase (Deno runtime) used for embeddings and search
- **Webhook**: Database trigger that calls Edge Function on INSERT (auto-embedding pipeline)
- **Groq**: Cloud API provider for Whisper voice transcription (whisper-large-v3-turbo)
- **Voice transcription**: Converting audio to text (Telegram voice messages → text via Groq)

### Work Domain Terms (User Context)

- **SLAM**: Simultaneous Localization and Mapping (robot navigation technique)
- **POMDP**: Partially Observable Markov Decision Process (decision-making under uncertainty)
- **FastSLAM**: SLAM algorithm using particle filters
- **Particle filter**: Monte Carlo method for state estimation
- **Loop closure**: Recognizing previously visited locations to correct accumulated error
- **LiDAR**: Light Detection and Ranging (laser-based distance sensor)
