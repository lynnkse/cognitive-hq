# cognitive-hq — Onboarding

## What this repository is

cognitive-hq is a template system for managing Claude context across stateless LLM sessions. It provides the `.claude/` directory structure and documentation for any project that wants to use the stateless-LLM workflow.

## How to understand the project

1. Read AGENT_RECREATION_GUIDE.md (complete system documentation)
2. Read .claude/LOG.md (decisions & reasoning)
3. Inspect .claude/TREE.txt (structure)

## How to use this for your own project

1. Create a `.claude/` directory in your project
2. Copy the template files from AGENT_RECREATION_GUIDE.md
3. Customize BOOTSTRAP.md, RULES.md, WORKFLOW.md for your project
4. Start logging decisions in LOG.md
5. Track tasks in TODO.md

## What NOT to assume

- No hidden design documents
- No implicit conventions not written in code or logs
- If unclear, ask and then log the answer
