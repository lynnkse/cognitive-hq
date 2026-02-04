# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repository Is

This is a **meta-project**: a template and documentation system for managing Claude context across stateless LLM sessions. It provides a filesystem-based memory system that allows Claude to maintain project continuity without relying on chat memory.

The primary documentation is `AGENT_RECREATION_GUIDE.md`, which contains complete instructions for setting up the `.claude/` directory structure in any project.

## Core Concepts

### Stateless-by-Design Workflow
- Claude cannot rely on chat memory; all project memory lives in the filesystem
- Every new session starts by reading canonical files
- Crash recovery: "Read BOOTSTRAP.md and proceed" restores full context

### Authority Hierarchy
1. **Code** = what the system does (ground truth)
2. **LOG.md** = human decisions and reasoning (authoritative)
3. **INTENT/** = what the system was meant to do (authoritative for intent)
4. **DERIVED_CONTEXT.DATA.md** = Claude's cached understanding (non-authoritative, disposable)

### Promotion Policy
Claude must never auto-promote information to canonical files. When information should be logged or formalized:
1. Explicitly suggest the promotion
2. Wait for human confirmation

## Directory Structure Template

```
.claude/
├── BOOTSTRAP.md              # Entry point - mandatory reads list
├── RULES.md                  # Hard constraints on behavior
├── WORKFLOW.md               # Stateless workflow protocol
├── STATE.md                  # Git commits (auto-populated)
├── LOG.md                    # Human decisions/observations (authoritative)
├── TODO.md                   # Task tracking
├── TREE.txt                  # Repository structure (auto-generated)
├── DERIVED_CONTEXT.md        # Rules for derived context handling
├── DERIVED_CONTEXT.DATA.md   # Claude's cached understanding (disposable)
├── ABSTRACTIONS.md           # Core terminology definitions
├── ONBOARDING.md             # New researcher guide
├── log.sh                    # Logging helper script
├── tree.sh                   # Tree generation script
└── INTENT/                   # Human-authored design intent
```

## Helper Scripts

Generate tree structure:
```bash
.claude/tree.sh
```

Log an entry:
```bash
.claude/log.sh "Your log message"
```

## When Using This System in a Project

1. Create `.claude/` directory
2. Copy template files from `AGENT_RECREATION_GUIDE.md`
3. Customize BOOTSTRAP.md, RULES.md, WORKFLOW.md for your project
4. Initialize empty STATE.md, LOG.md, TODO.md
5. Add project-specific terminology to ABSTRACTIONS.md

## Session Start Protocol

When starting a session on a project using this system:
1. Read BOOTSTRAP.md first
2. Follow its mandatory reads list
3. Treat DERIVED_CONTEXT.DATA.md as a cache, not truth
4. Base all conclusions on code and canonical files only
