# Core Abstractions (cognitive-hq)

This file defines terms used in logs and discussions.

---

## Terms

- **Canonical file**: A file that is authoritative source of truth (LOG.md, STATE.md, code)
- **Derived context**: Claude's cached understanding; non-authoritative and disposable
- **Promotion**: Moving information from derived context to a canonical file
- **Bootstrap**: The entry point file that lists mandatory reads for Claude sessions
- **Intent file**: Human-authored explanation of design goals and motivations
- **Stateless workflow**: Operating without relying on chat memory; all context from files
