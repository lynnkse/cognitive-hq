# Claude Working Protocol (cognitive-hq)

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
- Run: `.claude/tree.sh`
- Start Claude
- Ask Claude to summarize current project state

### When starting a task
Log intent:
```
.claude/log.sh "Goal: <short description>"
```

### During work
- Code normally
- Run tests as needed
- Do NOT narrate continuously

### When something important happens
Log events only:
- observations
- decisions
- hypotheses
- conclusions

Example:
```
.claude/log.sh "Observation: template structure works well for new projects"
.claude/log.sh "Decision: keep DERIVED_CONTEXT separate from LOG"
```

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
   "Read BOOTSTRAP.md and proceed."

Continuity is reconstructed from disk.

---

## One Rule to Remember

If it matters tomorrow, log it today.
If it matters to Claude, it must exist in the repo.
