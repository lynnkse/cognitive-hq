# DERIVED CONTEXT (Claude)

⚠️ WARNING
This file is a NON-AUTHORITATIVE, DERIVED, and DISPOSABLE cache of Claude's
current understanding of the cognitive-hq codebase.

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
