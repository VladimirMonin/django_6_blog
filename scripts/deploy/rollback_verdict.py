#!/usr/bin/env python3
"""Вычислять детерминированный verdict отката до изменения symlink."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from release_metadata import load_json, release_order, validate_metadata

UNKNOWN = "REFUSE_METADATA_OR_DB_UNKNOWN"


def live_leaves(project: Path) -> list[list[str]]:
    result = subprocess.run(
        [sys.executable, "manage.py", "showmigrations", "--plan"],
        cwd=project,
        check=True,
        text=True,
        capture_output=True,
    )
    leaves: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line.startswith("[X] "):
            continue
        label = line[4:].split()[0]
        if "." not in label:
            continue
        app, migration = label.split(".", 1)
        leaves[app] = migration
    return [[app, migration] for app, migration in sorted(leaves.items())]


def verdict(current: dict, target: dict, leaves: list[list[str]], schema: dict) -> str:
    try:
        validate_metadata(target, schema)
        validate_metadata(current, schema)
        if leaves != current["migration_leaves"]:
            return UNKNOWN
    except Exception:
        return UNKNOWN
    if release_order(target) >= release_order(current):
        return "REFUSE_NOT_ROLLBACK"
    if target["media_storage_mode"] != current["media_storage_mode"]:
        return "REFUSE_STORAGE_MODE"
    if target["schema_sequence"] > current["schema_sequence"]:
        return "REFUSE_TARGET_REQUIRES_NEWER_SCHEMA"
    if target["schema_sequence"] < current["minimum_compatible_schema_sequence"]:
        return "REFUSE_SCHEMA_TOO_OLD"
    if current["migration_safety"] in {"forward-only", "destructive"} and target["schema_sequence"] < current["schema_sequence"]:
        return "REFUSE_IRREVERSIBLE_BOUNDARY"
    if target["schema_sequence"] == current["schema_sequence"] and target["migration_leaves"] != current["migration_leaves"]:
        return "REFUSE_LEAF_MISMATCH"
    return "ALLOW_CODE_STATIC_ONLY"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--live-leaves-file", type=Path)
    parser.add_argument("--project", type=Path)
    args = parser.parse_args()
    try:
        current = load_json(args.current)
        target = load_json(args.target)
        schema = load_json(args.schema)
        if args.live_leaves_file:
            leaves = json.loads(args.live_leaves_file.read_text(encoding="utf-8"))
        elif args.project:
            leaves = live_leaves(args.project)
        else:
            raise ValueError("live migration evidence is required")
        result = verdict(current, target, leaves, schema)
    except Exception:
        result = UNKNOWN
    print(result)
    return 0 if result == "ALLOW_CODE_STATIC_ONLY" else 3


if __name__ == "__main__":
    raise SystemExit(main())
