# Learning Queue — Research & Implementation Candidates

This file tracks interesting concepts, techniques, and tools encountered during courses and research that might be worth implementing in cognitive-hq or related projects.

**Source:** Ongoing learning courses, tutorials, papers, documentation
**Purpose:** Capture ideas before they're forgotten, evaluate later for implementation

---

## Queue Structure

Items move through these states:
1. **Inbox** — Just captured, not yet evaluated
2. **Research** — Worth investigating further
3. **Implement** — Decided to build/integrate
4. **Archive** — Evaluated but not implementing (with reason)

---

## Inbox — Recently Captured

<!-- Add new items here as you encounter them -->

### Hierarchical CLAUDE.md Pattern (3-Level System)
**Source:** claude-telegram-relay observation + course discussion
**Date added:** 2026-02-14
**Brief description:** Multiple CLAUDE.md files at different directory levels for scoped context
**Current observation:**
- **Level 1 (Root):** `/CLAUDE.md` - Project philosophy, .claude/ system explanation
- **Level 2 (Module):** `/claude-telegram-relay/CLAUDE.md` - Operational setup guide, phase-by-phase
- **Level 3 (Component?):** Not yet implemented - could be per-subsystem guidance

**Potential use:**
- Improve context scoping (module-specific instructions without polluting global)
- Better separation: philosophy vs operations vs implementation details
- Could .claude/ directory benefit from similar hierarchy?

**Questions to research:**
1. How does Claude Code resolve multiple CLAUDE.md files? (reads all? nearest? root only?)
2. Should .claude/ structure also be hierarchical? (e.g., `module/.claude/LOG.md`)
3. What's the right boundary: CLAUDE.md (operational) vs .claude/ (state/memory)?
4. When to use nested .claude/ vs flat structure with prefixes?

**Priority:** MEDIUM
[SYSTEM] [ARCHITECTURE]

### Example Entry Template
**Concept:** [Name of technique/tool/idea]
**Source:** [Course name, video, paper, etc.]
**Date added:** YYYY-MM-DD
**Brief description:** One sentence explanation
**Potential use:** How it might apply to cognitive-hq or work projects
**Priority:** LOW | MEDIUM | HIGH

---

<!-- Example:
### Vector Database Optimization
**Source:** Database Course, Module 5
**Date added:** 2026-02-14
**Brief description:** HNSW indexing for faster similarity search
**Potential use:** Speed up Supabase semantic search (currently using basic cosine)
**Priority:** MEDIUM
-->

---

### Context Window Management
**Source:** Course + /context command observation
**Date added:** 2026-02-14
**Brief:** Managing 200k token context efficiently
**Research:**
- Manual vs autocompact strategies
- Minimize memory file token usage
- External memory (Supabase) vs in-context trade-offs
- Progressive summarization
- Context-aware subagent delegation
**Potential use:** Optimize .claude/ files, improve long conversations
**Priority:** LOW
[SYSTEM] [AI]

---

## Research — Worth Investigating

<!-- Items that passed initial filter, need deeper research -->

### Hierarchical CLAUDE.md Pattern (3-Level System)
**Source:** claude-telegram-relay observation + course discussion
**Date added:** 2026-02-14
**Date moved to Research:** 2026-02-14
**Brief description:** Multiple CLAUDE.md files at different directory levels for scoped context

**Initial analysis completed:** See `.claude/ANALYSIS_HIERARCHICAL_CONTEXT.md`

**Key findings:**
- CLAUDE.md (instructions, static) vs .claude/ (memory, dynamic) serve different purposes
- Current flat .claude/ structure is appropriate for cognitive-hq size
- Hierarchical .claude/ makes sense for 5+ active modules with independent lifecycles
- cognitive-hq doesn't need it yet (relay is separate repo, Python agent is legacy)

**Open research questions:**
1. How does Claude Code resolve multiple CLAUDE.md files in practice?
   - Experiment: Create nested CLAUDE.md and observe behavior
   - Does it merge? Priority order? Read all?
2. At what project size does flat .claude/ become unwieldy?
   - Monitor LOG.md size (currently ~500 lines, threshold ~1000?)
3. Best practices for splitting when needed (by year? by module? by concern?)

**Next steps:**
- Monitor LOG.md growth
- Re-evaluate if cognitive-hq adds 3+ new active modules
- Experiment with nested CLAUDE.md to understand resolution behavior
- Document findings back to analysis document

**Priority:** LOW (not needed now, but valuable pattern to understand)
**Status:** Analysis complete, monitoring phase
[SYSTEM] [ARCHITECTURE]

---

## Implement — Approved for Integration

<!-- Items decided to implement, waiting for scheduling -->

---

## Archive — Not Implementing

<!-- Items evaluated but decided against, with reasoning -->

### Why Archive?
- Already have equivalent solution
- Too complex for current needs
- Not applicable to our use case
- Cost/benefit doesn't justify
- Better alternatives exist

---

## Notes

- Keep entries concise (1-3 sentences max)
- Focus on actionable items, not general theory
- Tag with domains: `[ROBOTICS]`, `[AI]`, `[DATABASE]`, `[SYSTEM]`
- Link to TODO.md when moving to "Implement" state
- Archive liberally — it's okay to say no

---

*Last updated: 2026-02-14*
