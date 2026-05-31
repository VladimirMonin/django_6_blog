---
applyTo: "README.md,doc/**/*.md,AGENTS.md,.github/instructions/*.instructions.md"
name: "DOCS.Documentation"
description: "Use when updating README, doc/*.md, AGENTS.md, or .github/instructions: documentation structure, atomic docs, instruction style, routing, and what belongs in fundamental project instructions."
---

# DOCS — Documentation and instructions

## Structure

- `README.md` is the short human entry point.
- `doc/README.md` is the documentation catalog.
- Current operational docs live as atomic `doc/*.md` files.
- Historical plans, architecture serials and research reports stay in their subfolders and are references only.
- `AGENTS.md` is the agent router.
- `.github/instructions/*.instructions.md` contains atomic subsystem instructions.

## Atomicity

One document or instruction should cover one responsibility zone. Split instead of mixing unrelated topics.

## Instruction format

Instruction files use:

```text
PREFIX.topic.instructions.md
```

with YAML frontmatter first:

```yaml
---
applyTo: "glob"
name: "PREFIX.Topic"
description: "When to use this instruction: subsystem, files, trigger words."
---
```

`description` is a routing trigger, not a generic summary.

## What belongs in instructions

Include only durable project rules:

- architecture boundaries;
- safety gates;
- stable data/UI contracts;
- testing and visual QA obligations;
- commit safety;
- documentation maintenance rules.

Do not include release notes, temporary task progress, long logs, one-off implementation history or stale plans.

## Sync rule

When behavior changes, update the matching doc in the same slice. If an instruction changes, keep `AGENTS.md` routing synchronized.
