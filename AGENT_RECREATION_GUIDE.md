# Claude Context Recreation Guide

This document provides all information needed by another Claude agent to recreate the `.claude/` directory structure for the ANPLOS project.

---

## Directory Structure

```
.claude/
├── BOOTSTRAP.md          # Entry point for Claude sessions
├── RULES.md              # Hard constraints on Claude behavior
├── WORKFLOW.md           # Stateless-LLM workflow protocol
├── STATE.md              # Git commits and structural changes (auto-populated)
├── LOG.md                # Human decisions, observations, hypotheses
├── TODO.md               # Active/pending/completed tasks
├── TREE.txt              # Repository structure snapshot (auto-generated)
├── DERIVED_CONTEXT.md    # Rules for derived context handling
├── DERIVED_CONTEXT.DATA.md # Non-authoritative cached understanding
├── ABSTRACTIONS.md       # Core terminology definitions
├── ONBOARDING.md         # New researcher guide
├── settings.local.json   # Local Claude settings (permissions)
├── log.sh                # Helper script for logging
├── tree.sh               # Helper script for tree generation
└── INTENT/
    ├── README.md         # What intent files are
    └── REFERENCES/
        ├── Sunberg18icaps.pdf          # Reference paper
        └── Sunberg18icaps.intent.md    # Paper notes
```

---

## File Contents

### 1. BOOTSTRAP.md (Entry Point)

Purpose: First file Claude reads. Lists mandatory reads before reasoning.

```markdown
# Claude Bootstrap — ANPLOS

You are assisting with the ANPLOS research codebase.

This is a stateless-by-design workflow.
You must not rely on prior chat memory.

---

## Mandatory Reads (always)

Read these files fully before reasoning:

- .claude/RULES.md
- .claude/WORKFLOW.md
- .claude/STATE.md
- .claude/LOG.md
- .claude/TODO.md
- .claude/TREE.txt
- .claude/DERIVED_CONTEXT.md

---

## Derived Context (special handling)

If present, also read:

- .claude/DERIVED_CONTEXT.DATA.md

Important:
- This file is NON-AUTHORITATIVE
- It may be incomplete, outdated, or wrong
- It exists only to accelerate reasoning
- It must never be treated as ground truth

You may update or rewrite DERIVED_CONTEXT.DATA.md,
but you must obey the rules defined in DERIVED_CONTEXT.md.

---

## Human Intent (authoritative, non-implementation)

If relevant to the task, read files under:

- .claude/INTENT/

These files contain human-authored explanations of:
- design motivations
- conceptual models
- assumptions not explicit in code
- tradeoffs and known limitations
- future goals or desired features

Rules:
- Intent files are AUTHORITATIVE about *intent*
- Intent files may contradict current code
- When intent and code differ:
  - treat intent as the goal
  - treat code as the current approximation
- Intent files must NOT be treated as proof of correctness

Do NOT modify intent files unless explicitly asked.

---

## Conditional Reads (only if relevant)

Read the following ONLY if needed for the task:

- .claude/ABSTRACTIONS.md
  (for theory, terminology, or conceptual alignment)

- .claude/ONBOARDING.md
  (for summarizing the project or helping new researchers)

---

## Reasoning Rules

- Base conclusions strictly on code and canonical files
- Treat derived context as a cache, not truth
- Use intent to interpret *why*, not *what*
- Ask when information is missing or ambiguous
- Prefer explicit references to files or code locations

---

## Promotion Policy (hard constraint)

You must NOT promote information automatically.

If you believe something should be logged:
- Explicitly SUGGEST it
- WAIT for human confirmation
```

---

### 2. RULES.md

Purpose: Hard constraints on Claude behavior.

```markdown
You are assisting with the ANPLOS / Julia POMDP codebase.

Rules:
1. Read STATE.md and TREE.txt before reasoning
2. Assume no prior chat memory
3. Base conclusions on code + logs only
4. Ask if something is unclear instead of guessing
5. Prefer small, reversible changes
```

---

### 3. WORKFLOW.md

Purpose: Defines stateless-LLM workflow protocol.

```markdown
# Claude Working Protocol (ANPLOS)

This repository uses a stateless-LLM workflow.
Claude does NOT rely on chat memory.
All project memory lives in the filesystem.

---

## Canonical Project Memory

Claude must always read the following files before reasoning:

1. .claude/RULES.md   — hard constraints and behavior rules
2. .claude/STATE.md   — commits and structural changes
3. .claude/LOG.md     — human decisions, observations, hypotheses
4. .claude/TODO.md    — active tasks, subtasks, and completion status
5. .claude/TREE.txt   — current repository structure

If information is not in these files or in the codebase,
it must be treated as unknown.

---

## Daily Workflow (Human)

### Start of work
- Run: `claude-tree`
- Start Claude
- Ask Claude to summarize current project state

### When starting a task
Log intent:
claude-log "Goal: <short description>"

### During work
- Code normally
- Run tests / ROS / Julia
- Do NOT narrate continuously

### When something important happens
Log events only:
- observations
- decisions
- hypotheses
- conclusions

Example:
claude-log "Observation: belief tree collapses after depth 3"
claude-log "Hypothesis: UCB dominated by prior"


### Commits
- All git commits are auto-logged into STATE.md
- No extra explanation required

---

## Asking Claude for Help

Claude questions must be grounded in artifacts.

Good:
- "Based on LOG and recent commits, suggest causes"
- "Given TREE.txt, where should this module live?"

Bad:
- "You remember we discussed earlier…"
- "As before…"

Claude must reason from files, not memory.

---

## Crash / Restart Protocol

If Claude, tmux, or SSH crashes:

1. Restart Claude
2. Ask:
   "Read RULES.md, STATE.md, LOG.md, TODO.md, TREE.txt and continue."

Continuity is reconstructed from disk.

---

## One Rule to Remember

If it matters tomorrow, log it today.
If it matters to Claude, it must exist in the repo.
```

---

### 4. STATE.md

Purpose: Auto-populated with git commits. Usually starts empty or with header.

```markdown
# STATE — Git Commits
```

(Populated by hooks or manual logging)

---

### 5. LOG.md

Purpose: Human decisions, observations, hypotheses. The authoritative record.

**Structure:**
```markdown
# Project Log — ANPLOS

This file records human decisions, observations, hypotheses, and conclusions.
It is the authoritative source of project history and reasoning.

---

### YYYY-MM-DD — Topic Title

Content goes here...

---
```

**Current size:** ~2600 lines covering MCTS optimization, tree visualization, rollout fixes, semantic planner design.

**Recent key entries:**
- Progressive Widening parameter sweeps
- Rollout implementation for Transform3D beliefs
- MCTS tree visualization integration
- Semantic planner pipeline design (DA → Belief → Semantic Planner)
- Object-level DA hypothesis requirements

---

### 6. TODO.md

Purpose: Task tracking with status, priority, and implementation phases.

**Structure:**
```markdown
# TODO — ANPLOS Project Tasks

This file tracks active, pending, and completed tasks for the ANPLOS project.
It is the authoritative source for task management alongside LOG.md.

---

## Active Tasks

_No active tasks_

---

## Pending Tasks

### [ ] Task Title
**Priority:** HIGH/MEDIUM/LOW
**Created:** YYYY-MM-DD
**Status:** Not Started / In Progress

**Context:**
...

**Investigation Steps:**
1. Step one
2. Step two

---

## Completed Tasks

### [x] Completed Task Title
**Completed:** YYYY-MM-DD
**Outcome:** What was achieved

---

## Task Lifecycle

1. **Active**: Currently being worked on
2. **Pending**: Planned but not started (may have blockers)
3. **Completed**: Done with documented outcome
4. **Deferred**: Postponed (with reason)
5. **Cancelled**: No longer relevant (with reason)
```

**Current pending tasks:**
- Investigate Robot Not Moving Toward Goal (HIGH)
- Q-Value Normalization in UCB (LOW, deferred)
- Try POMCPOW Algorithm (LOW)
- Investigate Shallow MCTS Trees (HIGH)
- Solve Object-Level Data Association (HIGH)
- Implement Semantic Planner Pipeline (HIGH, IN PROGRESS - phased plan)

---

### 7. TREE.txt

Purpose: Repository structure snapshot. Auto-generated by `tree.sh`.

Generated command:
```bash
tree -a -l -L 5 \
  -I ".git|build|devel|install|logs|log|__pycache__|\.venv|..." \
  "$REPO_ROOT" > "$SCRIPT_DIR/TREE.txt"
```

---

### 8. DERIVED_CONTEXT.md

Purpose: Rules for how to handle derived (non-authoritative) context.

```markdown
# DERIVED CONTEXT (Claude)

⚠️ WARNING
This file is a NON-AUTHORITATIVE, DERIVED, and DISPOSABLE cache of Claude's
current understanding of the ANPLOS codebase.

- It MAY be incomplete
- It MAY be outdated
- It MAY be wrong
- It MAY be rewritten or discarded at any time

Nothing in this file is ground truth.

Ground truth lives in:
- the code
- .claude/LOG.md
- .claude/STATE.md
- .claude/ABSTRACTIONS.md

This file exists ONLY to accelerate reasoning.

---

## Purpose

This document captures Claude's *current mental model* of the system:
- architectural intuition
- inferred relationships
- suspected invariants
- risk areas
- open questions

---

## Rules of Use (MANDATORY)

1. This file MUST NOT be treated as authoritative.
2. This file MUST NOT replace human-written logs or abstractions.
3. This file MUST NOT be relied upon for correctness.
4. This file MAY be regenerated from scratch at any time.
5. Deleting this file MUST NOT break the workflow.

---

## Promotion Policy (CRITICAL)

Claude MUST NOT promote information automatically.

When Claude believes something here is important enough to become canonical,
it must ONLY do the following:

- Explicitly SUGGEST promotion
- WAIT for human confirmation.

Only the human decides whether to:
- log it in LOG.md
- formalize it in ABSTRACTIONS.md
- encode it in code or documentation
- ignore it

Claude must never write to canonical files on its own initiative.
```

---

### 9. DERIVED_CONTEXT.DATA.md

Purpose: The actual cached understanding (non-authoritative).

**Current contents cover:**
- MCTS Planning System Architecture
- Julia-Python Bridge Pattern
- Tree Visualization Pipeline
- MCTS Performance Characteristics
- Q-Value Interpretation
- MCTS Horizon Limitation Analysis
- Progressive Widening Parameter Effects
- Odometry Queue fixes
- DA Vision Pipeline Architecture
- Semantic Objects & Data Association
- Semantic Object Pipeline (DA → Belief → Semantic Planner)

---

### 10. ABSTRACTIONS.md

Purpose: Core terminology definitions.

```markdown
# Core Abstractions (ANPLOS)

- Belief: probabilistic representation of robot/world state
- Factor Graph: GTSAM graph encoding belief
- Action Consistency (AC): property relating belief updates across agents
- Planner: produces actions by reasoning over belief space
- Inference: updates belief from observations

This file defines terms used in logs and discussions.
```

---

### 11. ONBOARDING.md

Purpose: New researcher guide.

```markdown
# ANPLOS — Researcher Onboarding

## What this repository is
ANPLOS is a research codebase for belief-space planning,
active SLAM, and multi-robot systems using ROS, GTSAM, and Julia POMDPs.

## How to understand the project
1. Read .claude/LOG.md (decisions & reasoning)
2. Read .claude/STATE.md (how code evolved)
3. Inspect .claude/TREE.txt (structure)
4. Explore code top-down

## What NOT to assume
- No hidden design documents
- No implicit conventions not written in code or logs
- If unclear, ask and then log the answer

## Where to start coding
- Planning logic: <path>
- Inference logic: <path>
- Experiments: <path>
```

---

### 12. settings.local.json

Purpose: Local Claude permissions.

```json
{
  "permissions": {
    "allow": [
      "Bash(pip install:*)",
      "Bash(true)",
      "Bash(find:*)",
      "Bash(julia:*)",
      "Bash(tee:*)",
      "Bash(python3:*)",
      "Bash(ls:*)",
      "Bash(chmod:*)",
      "Bash(done)",
      "Bash(./run_sweep.sh:*)"
    ],
    "deny": []
  }
}
```

---

### 13. log.sh

Purpose: Helper script for logging.

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
LOG_FILE="$SCRIPT_DIR/LOG.md"

if [[ ! -f "$LOG_FILE" ]]; then
  echo "ERROR: LOG.md not found at $LOG_FILE" >&2
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "ERROR: claude-log requires a message" >&2
  exit 1
fi

{
  echo "### $(date)"
  echo "$*"
  echo
} >> "$LOG_FILE"
```

---

### 14. tree.sh

Purpose: Helper script for generating TREE.txt.

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_PATH="$(readlink -f "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Follow symlinks (-l) so the Julia repo is expanded.
# Prune noisy / huge dirs so TREE.txt stays useful for reasoning.
tree -a -l -L 5 \
  -I ".git|build|devel|install|logs|log|__pycache__|\.venv|\.mypy_cache|\.pytest_cache|\.cache|node_modules|\.idea|\.vscode|cmake-build-.*|results|mr_results|mr_logs" \
  "$REPO_ROOT" > "$SCRIPT_DIR/TREE.txt"
```

---

### 15. INTENT/README.md

Purpose: Explains what intent files are.

```markdown
# Human Intent — ANPLOS

This directory contains **human-authored explanations of intent**.

It captures how the system is *meant* to work,
why certain design decisions were made,
and what future directions are envisioned —
independently of current implementation.

---

## What This Is

Files in this directory represent:

- conceptual explanations
- design motivations
- assumptions not explicit in code
- tradeoffs knowingly accepted
- ideas that guided implementation
- features that were planned but not implemented

---

## Authority Model

- Intent files are **authoritative about intent**
- Code is **authoritative about current behavior**
- When they conflict:
  - intent defines the *goal*
  - code reflects the *current approximation*

---

## Editing Rules

- Claude must NOT modify intent files unless explicitly instructed
- Claude may reference intent files to interpret code
- Claude may suggest that intent be updated or clarified
- Claude must never treat intent as proof of correctness
```

---

## Key Principles of This System

1. **Stateless by design**: Claude cannot rely on chat memory. Everything must be in files.

2. **Authority hierarchy**:
   - Code = what the system does
   - LOG.md = human decisions and reasoning (authoritative)
   - INTENT/ = what the system was meant to do (authoritative for intent)
   - DERIVED_CONTEXT.DATA.md = Claude's cached understanding (non-authoritative, disposable)

3. **Promotion policy**: Claude never auto-promotes information. Only humans decide what becomes canonical.

4. **Crash recovery**: "Read BOOTSTRAP.md and proceed" restores full context.

5. **If it matters, log it**: Future Claude sessions only know what's written down.

---

## Project-Specific Context (ANPLOS)

**What ANPLOS is:**
- ROS-based multi-robot belief space planning system
- Uses GTSAM for factor graphs
- Uses Julia for MCTS planning (PFT-DPW algorithm)
- Python for ROS nodes and orchestration

**Key technical areas:**
- MCTS tree visualization and analysis
- Rollout implementation for Transform3D beliefs
- Progressive widening parameter tuning
- Semantic planner pipeline (new work in progress)
- Object-level data association for semantic objects

**Current active work:**
- Semantic planner for Tuvy's publication
- Object tracking with hypothesis handling
- Integration of semantic objects into belief system

---

## Recreation Instructions

To recreate this structure for a new project:

1. Create `.claude/` directory
2. Create BOOTSTRAP.md as the entry point
3. Create RULES.md, WORKFLOW.md (adjust to project needs)
4. Create empty STATE.md, LOG.md, TODO.md
5. Create DERIVED_CONTEXT.md (rules file) and DERIVED_CONTEXT.DATA.md (empty, to be filled)
6. Create ABSTRACTIONS.md with project-specific terminology
7. Create ONBOARDING.md for new team members
8. Add helper scripts (log.sh, tree.sh)
9. Optionally create INTENT/ for design documentation

**Important:** The content of LOG.md, TODO.md, and DERIVED_CONTEXT.DATA.md is project-specific and accumulates over time through usage.

---

*Created: 2026-02-03*
*Purpose: Enable another Claude agent to understand and recreate this context management system*
