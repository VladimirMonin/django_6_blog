"""Small, strict environment parsing helpers for Django settings."""

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


def env_required(name: str) -> str:
    """Return a non-empty environment value or fail settings import."""
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


def env_int(name: str, default: int) -> int:
    """Read an integer environment variable."""
    try:
        return int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise RuntimeError(f"Environment variable must be an integer: {name}") from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """Read a comma-separated env var into a cleaned list."""
    value = os.environ.get(name)
    if value is None:
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
