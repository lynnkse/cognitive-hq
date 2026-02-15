# Claude Bootstrap — cognitive-hq

You are assisting with the cognitive-hq repository.

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

- .claude/LEARNING_QUEUE.md
  (for research items from courses/papers to evaluate for implementation)

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
