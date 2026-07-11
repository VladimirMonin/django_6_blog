---
applyTo: "**"
name: "DOCS.Git"
description: "Use when inspecting, staging, committing, or pushing django_6_blog changes: staged-diff truth, secret/local-artifact checks, conventional commit prefixes, and explicit commit/push authorization."
---

# DOCS — Git discipline

## Authorization and source of truth

- Commit and push only when the user explicitly requests them.
- Before staging, inspect `git status --short --branch`, unstaged/staged diffs, and untracked files.
- Before committing, inspect the complete staged diff. The staged diff—not the plan, worktree, logs, or task report—is the source of truth for commit scope and message.
- Do not paste command output or test logs into commit messages.

## Safety gate

Run before commit:

```bash
git diff --cached --check
git diff --cached --name-only | grep -E '(^\.env$|^\.venv/|^\.hermes/|^\.serena/|^db\.sqlite3$|^media/posts/|^tests/assets/|__pycache__|\.pyc$)' && exit 1 || true
git diff --cached | grep -En '(AKIA|SECRET|TOKEN|PASSWORD|PASS|API[_-]?KEY|BEGIN RSA|BEGIN OPENSSH|ghp_|sk-|xoxb-|gsk_)' && exit 1 || true
```

Treat scan matches as review prompts: inspect them and remove real secrets or forbidden local artifacts before committing.

## Commit message

Choose the prefix from the actual staged change:

- `feat:` — new feature;
- `fix:` — bug fix;
- `docs:` — documentation changes;
- `style:` — formatting or visual/style-only changes;
- `refactor:` — behavior-preserving code restructuring;
- `test:` — tests-only changes;
- `chore:` — maintenance.

Keep the subject concise and imperative. Add a short body only when it materially helps review; never claim unstaged work.

After a requested commit succeeds, inspect branch status before any separately requested push.
