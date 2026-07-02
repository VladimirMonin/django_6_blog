---
applyTo: "AGENTS.md,doc/kanban.md,doc/agent-workflow.md"
name: "AGENT.Kanban"
description: "Use when creating, editing, dispatching, reviewing, or reporting Hermes Kanban cards for django_6_blog: board slug, card contract, dependencies, CLI source of truth, dispatch boundary, and final commit/push gate."
---

# AGENT — Kanban workflow

## Board

Use the dedicated Hermes Kanban board:

```text
slug: django-6-blog
name: Django 6 Blog
default workdir: /home/v/code/django_6_blog
```

The Kanban CLI/database is the source of truth. Browser dashboard and Telegram notifications are reporting layers.

## Before creating cards

1. Confirm the project is `django_6_blog` and repo is `/home/v/code/django_6_blog`.
2. Read `AGENTS.md`.
3. Read relevant `instructions/*.instructions.md` and `doc/*.md` for the slice.
4. Check existing board state:

   ```bash
   hermes kanban --board django-6-blog list
   hermes kanban --board django-6-blog stats
   ```

Do not create a second project board unless the user explicitly asks for a separate workstream.

## Card contract

Every code or documentation card must include:

- exact repo/workdir;
- files/instructions to read first;
- one narrow task;
- measurable done condition;
- required evidence: tests, browser QA, API check, docs sync, or explicit waiver;
- short Russian reporting rule.

Avoid vague cards such as "improve UI" or "check API" without scope and proof.

## Dependencies

Use dependencies to model gates:

- implementation/audit cards feed review or quality cards;
- docs/instructions sync follows behavior-changing cards;
- final self-check/commit/push card depends on all cards in the wave.

Do not mark final commit/push done until upstream cards are done or explicitly waived by the user.

## Dispatch boundary

Creating cards is not the same as starting autonomous work.

Only run `dispatch` when:

- cards are concrete;
- dependencies are sane;
- assignee/profile strategy is clear;
- the user expects autonomous execution.

For planning/probe boards, do not run dispatch automatically.

## Reporting

Telegram reports must be short and Russian-first:

- current state;
- what changed;
- what was verified;
- blocker/input if any.

Do not dump raw board state or long logs unless asked.

## Commit and push

Commit/push is a final gate, not a side effect of any random card.

Before commit:

```bash
git status --short --branch
git diff --stat
git diff --cached --stat
git ls-files --others --exclude-standard
uv lock --check
uv run python manage.py check
uv run pytest -q
git diff --check
```

Do not stage `.env`, `.venv/`, `db.sqlite3`, `media/posts/*`, `tests/assets/*`, `__pycache__/`, `*.pyc`, generated caches, or secrets.
