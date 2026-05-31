---
applyTo: "**/*.py"
name: "DOCS.PythonDocstrings"
description: "Use when adding or changing Python docstrings in django_6_blog modules, functions, classes, services, management commands, tests, and helpers."
---

# DOCS — Python docstrings

## Language and style

- Write project docstrings in Russian unless a public library/API convention requires English.
- Keep docstrings factual and short.
- Prefer type hints in function signatures; do not duplicate obvious types in docstrings.

## Modules

Use a module docstring when the file has a meaningful responsibility that is not obvious from its path.

Good module docstring shape:

```python
"""Import local Obsidian/Markdown notes into blog posts."""
```

Do not add long module inventories that duplicate the code.

## Functions and methods

Use Google-style sections only when they add information:

- `Args` for non-obvious parameters;
- `Returns` for non-obvious return contracts;
- `Raises` for expected domain errors.

Skip docstrings for trivial private helpers, simple getters, one-line wrappers and tests whose assertion names are already clear.

## Classes

Class docstrings should explain responsibility, not list every field. Model field meanings belong in model definitions, docs or tests when they are user-facing contracts.

## Keep current

When behavior changes, update or remove stale docstrings in the same slice. A stale docstring is worse than no docstring.
