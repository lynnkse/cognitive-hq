# Human Intent — cognitive-hq

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
