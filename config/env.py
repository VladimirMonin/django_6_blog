"""Small environment helpers for local Django settings.

The project stays SQLite-only for now. Values are read from process
environment; local developers can copy .env.example into .env and export it
with their shell or editor if needed.
"""

from __future__ import annotations

import os


def env(name: str, default: str = "") -> str:
    """Read a string environment variable with a default."""
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    """Read a boolean env var using common truthy strings."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Read a comma-separated env var into a cleaned list."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
