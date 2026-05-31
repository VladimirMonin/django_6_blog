---
applyTo: "**"
name: "DOCS.CommitMessages"
description: "Use when writing commit messages for django_6_blog: conventional prefix, concise summary, optional Russian bullet body for multi-file documentation or feature slices."
---

# DOCS — Commit messages

## Prefixes

Use short English prefixes:

- `feat:` — new feature;
- `bugfix:` — bug fix;
- `hotfix:` — urgent fix;
- `docs:` — documentation changes;
- `style:` — formatting or visual/style-only changes;
- `refactor:` — behavior-preserving code restructuring;
- `test:` — tests-only changes;
- `chore:` — maintenance.

## Summary

Keep the first line concise and in the imperative/summary style:

```text
docs: add project documentation and agent instructions
```

For phase-specific work, a phase prefix is allowed if the user or active plan asks for it:

```text
phase 4.3 feat: Добавлены медиа-типы записей
```

## Body

Use a body only when it helps future review. Bullets may be in Russian. Do not paste logs.

```text
docs: add project documentation and agent instructions

- Обновлена README-точка входа
- Добавлены атомарные документы в doc/
- Синхронизированы AGENTS.md и instructions/
```

## Safety

Do not invent a commit message before checking the actual staged diff. The message must describe what is staged, not what was planned.
