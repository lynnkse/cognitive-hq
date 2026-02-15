# Analysis: Hierarchical Context Management
## Could .claude/ Benefit from Multi-Level CLAUDE.md Pattern?

**Date:** 2026-02-14
**Status:** Research phase
**Reference:** LEARNING_QUEUE.md

---

## Current Observation: 3-Level CLAUDE.md Pattern

### Level 1: Root Project Context
**File:** `/cognitive-hq/CLAUDE.md`
**Purpose:** Philosophy and system overview
**Content:**
- What the repository is (meta-project)
- Core concepts (stateless workflow, authority hierarchy)
- .claude/ directory structure template
- Session start protocol
- High-level guidance for Claude Code

**Scope:** Entire project
**Style:** Conceptual, explanatory

### Level 2: Module Operational Guide
**File:** `/cognitive-hq/claude-telegram-relay/CLAUDE.md`
**Purpose:** Step-by-step setup and operation
**Content:**
- How this specific module works
- Phase-by-phase setup instructions
- Conversational guidance ("walk user through...")
- Testing and verification steps
- Troubleshooting

**Scope:** Single module (relay bot)
**Style:** Procedural, interactive

### Level 3: Component Instructions (Hypothetical)
**File:** `/cognitive-hq/src/runner/CLAUDE.md` (doesn't exist yet)
**Purpose:** Implementation-level guidance
**Potential content:**
- How specific subsystem works
- Key functions and their contracts
- Testing approaches
- Common modifications

**Scope:** Component/subsystem
**Style:** Technical, implementation-focused

---

## Current .claude/ Structure (Flat, Centralized)

```
cognitive-hq/
├── CLAUDE.md                    # Level 1: Project philosophy
├── .claude/                     # Centralized project context
│   ├── BOOTSTRAP.md            # Entry point, mandatory reads
│   ├── RULES.md                # Hard constraints
│   ├── WORKFLOW.md             # Process protocols
│   ├── STATE.md                # Current state
│   ├── LOG.md                  # Decisions & history
│   ├── TODO.md                 # Task tracking
│   ├── LEARNING_QUEUE.md       # Research items
│   ├── ABSTRACTIONS.md         # Terminology
│   └── INTENT/                 # Design intent docs
│
├── claude-telegram-relay/       # Separate repo/module
│   ├── CLAUDE.md               # Level 2: Module operations
│   └── (no .claude/ directory)
│
└── src/                         # Python agent (legacy)
    └── (no .claude/ or CLAUDE.md)
```

**Current pattern:**
- **CLAUDE.md:** Instructions for Claude Code (how to work with code)
- **.claude/:** Project memory and state (decisions, tasks, logs)
- **Separation:** One is operational, one is historical

---

## Question: Should .claude/ Be Hierarchical?

### Option A: Nested .claude/ Directories (Module-Scoped)

```
cognitive-hq/
├── .claude/                           # Project-wide context
│   ├── BOOTSTRAP.md
│   ├── LOG.md                         # High-level decisions
│   ├── TODO.md                        # Cross-module tasks
│   └── ...
│
├── claude-telegram-relay/
│   ├── CLAUDE.md                      # Module operations
│   └── .claude/                       # Module-specific context
│       ├── LOG.md                     # Relay-specific decisions
│       ├── TODO.md                    # Relay-specific tasks
│       └── STATE.md                   # Relay state
│
└── src/
    ├── CLAUDE.md                      # Python agent operations
    └── .claude/
        ├── LOG.md                     # Agent-specific log
        └── TODO.md                    # Agent-specific tasks
```

**Pros:**
- ✅ Better scoping (relay decisions don't pollute main LOG)
- ✅ Modules can be moved/deleted cleanly
- ✅ Each module is self-contained
- ✅ Clearer separation of concerns

**Cons:**
- ❌ Fragmented context (have to read multiple LOGs)
- ❌ Cross-module decisions unclear where to log
- ❌ More complex BOOTSTRAP (which .claude/ to read?)
- ❌ Harder to search/grep across all decisions

### Option B: Flat .claude/ with Prefixed Files (Current Approach)

```
cognitive-hq/
├── .claude/
│   ├── BOOTSTRAP.md
│   ├── LOG.md                   # All decisions in one place
│   ├── TODO.md                  # All tasks in one place
│   ├── STATE.md
│   ├── RELAY_SETUP.md           # Module-specific docs if needed
│   └── ...
│
├── claude-telegram-relay/
│   └── CLAUDE.md                # Operations only
│
└── src/
    └── CLAUDE.md                # Operations only (if needed)
```

**Pros:**
- ✅ Single source of truth for history
- ✅ Easy to grep/search all decisions
- ✅ Simpler BOOTSTRAP (one .claude/ to read)
- ✅ Cross-module context naturally captured

**Cons:**
- ❌ LOG.md can get very long
- ❌ Module decisions mixed with project decisions
- ❌ Moving/deleting modules leaves orphaned context
- ❌ Harder to see module-specific state at a glance

### Option C: Hybrid (Best of Both?)

```
cognitive-hq/
├── .claude/                           # Project-wide only
│   ├── BOOTSTRAP.md
│   ├── LOG.md                         # Cross-cutting decisions
│   ├── TODO.md                        # Project-level tasks
│   ├── MODULES.md                     # Index of modules and their .claude/
│   └── ...
│
├── claude-telegram-relay/
│   ├── CLAUDE.md                      # Operations guide
│   ├── .claude/                       # Module context
│   │   ├── MODULE_BOOTSTRAP.md        # What to read for this module
│   │   ├── LOG.md                     # Module-specific decisions
│   │   └── TODO.md                    # Module-specific tasks
│   └── ...
│
└── src/
    ├── CLAUDE.md
    └── .claude/
        ├── MODULE_BOOTSTRAP.md
        └── LOG.md
```

**Root .claude/BOOTSTRAP.md would say:**
```markdown
## Mandatory Reads
- .claude/LOG.md (project-wide decisions)
- .claude/TODO.md (project-level tasks)

## Module-Specific Context
If working on a specific module, also read:
- module/.claude/MODULE_BOOTSTRAP.md
- Follow that module's mandatory reads
```

**Pros:**
- ✅ Clear separation: project vs module
- ✅ Can search project-wide or module-specific
- ✅ Modules are self-contained but indexed
- ✅ Cross-module context in root, details in modules

**Cons:**
- ❌ More complexity (which BOOTSTRAP to read?)
- ❌ Potential duplication/inconsistency
- ❌ Need discipline about where to log things

---

## Analysis: CLAUDE.md vs .claude/ Directory

### Observed Pattern

**CLAUDE.md is for:**
- Instructions to Claude Code (how to work with the code)
- Operational procedures (setup, testing, workflows)
- Interactive guidance (conversational, phase-by-phase)
- **Static, rarely changes**

**.claude/ is for:**
- Project state and memory (decisions, tasks, logs)
- Historical record (what was done and why)
- Living documents (frequently updated)
- **Dynamic, changes every session**

### Key Insight

**CLAUDE.md = Instructions (for Claude)**
**.claude/ = Memory (for project continuity)**

They serve different purposes! CLAUDE.md tells Claude how to behave, .claude/ tells Claude what happened.

**Example:**
- `CLAUDE.md`: "When setting up, guide user through 7 phases conversationally"
- `.claude/LOG.md`: "2026-02-14 — Completed setup, chose Groq over local Whisper because..."

---

## Recommendation

### For cognitive-hq specifically:

**Keep current flat .claude/ structure**, because:

1. **Project is already modular via repo structure**
   - `claude-telegram-relay/` is a separate cloned repo (not part of cognitive-hq git)
   - `src/` Python agent is superseded (legacy)
   - No need to scope .claude/ when modules are already isolated

2. **Cross-cutting context is valuable**
   - Decision to switch from Python agent to relay (logged in root .claude/LOG.md)
   - This spans modules — hierarchical .claude/ would fragment this

3. **Current size is manageable**
   - LOG.md is ~500 lines (reasonable for single file)
   - Can split later if it becomes unwieldy

4. **LEARNING_QUEUE.md already added for scoped concerns**
   - Module-specific research items can use tags: `[RELAY]`, `[AGENT]`
   - Similar pattern could apply to other files if needed

### When hierarchical .claude/ makes sense:

**Use nested .claude/ when:**
- Large monorepo with 5+ active modules
- Modules have independent lifecycles (different teams, different release cycles)
- Module-specific state needs isolation (e.g., separate TODO lists with different priorities)
- Modules might be extracted to separate repos later

**cognitive-hq doesn't fit this yet** — relay is already separate, Python agent is legacy.

### Actionable Pattern to Consider

**If cognitive-hq grows to have multiple active modules:**

1. Keep root `.claude/` for project-wide context
2. Add module-specific `.claude/` only when needed
3. Create `.claude/MODULES.md` as index:
   ```markdown
   ## Active Modules
   - claude-telegram-relay/ → External repo (has own CLAUDE.md)
   - cognitive-agent-v2/ → .claude/ for module-specific state
   - tools-library/ → No .claude/ (no state needed)
   ```

4. Update BOOTSTRAP.md with conditional reads:
   ```markdown
   If working on a specific module, also read:
   - module/.claude/MODULE_BOOTSTRAP.md (if exists)
   ```

---

## Decision Framework

**Use hierarchical .claude/ if:**
- ✅ You have 5+ active modules with separate concerns
- ✅ Modules maintained by different people/teams
- ✅ Module state needs isolation
- ✅ Modules might split into separate repos

**Stick with flat .claude/ if:**
- ✅ Single developer or small team
- ✅ Cross-module context is important
- ✅ Project-wide view is more valuable than module isolation
- ✅ Can manage with tags/prefixes for scoping

**For cognitive-hq right now:** Flat .claude/ is correct.

**Monitor:** If relay gets complex enough to need its own state tracking, consider adding `claude-telegram-relay/.claude/` then.

---

## Next Steps

1. **Research:** How does Claude Code actually resolve multiple CLAUDE.md files?
   - Does it read all in tree?
   - Priority order (nearest to working directory wins)?
   - Experiment needed

2. **Document current pattern:**
   - CLAUDE.md = instructions (static)
   - .claude/ = memory (dynamic)
   - This distinction should be in ABSTRACTIONS.md

3. **Monitor LOG.md size:**
   - If it exceeds 1000 lines, consider splitting by year: `LOG_2026.md`
   - Or by module: `LOG_RELAY.md`, `LOG_AGENT.md`
   - Keep index in main LOG.md

4. **Add to LEARNING_QUEUE.md** ✅ (already done)
   - Mark for periodic review
   - Re-evaluate when project structure changes

---

*Analysis complete: 2026-02-14*
*Recommendation: Keep flat .claude/ for now, revisit if project grows to 5+ active modules*
