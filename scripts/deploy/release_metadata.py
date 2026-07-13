#!/usr/bin/env python3
"""Генерировать и проверять метаданные релиза без доступа к сети."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator

RELEASE_ID_RE = re.compile(r"^(\d{8}T\d{6}Z)-([0-9a-f]{12})$")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def release_order(metadata: dict) -> tuple[str, str]:
    return metadata["created_at"], metadata["commit"]


def validate_metadata(metadata: dict, schema: dict, predecessor: dict | None = None) -> None:
    Draft202012Validator(schema).validate(metadata)
    match = RELEASE_ID_RE.fullmatch(metadata["release_id"])
    if not match:
        raise ValueError("release_id is inconsistent")
    created = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    if metadata["created_at"] != created.isoformat(timespec="seconds").replace("+00:00", "Z"):
        raise ValueError("created_at is inconsistent with release_id")
    if metadata["commit"][:12] != match.group(2):
        raise ValueError("commit is inconsistent with release_id")
    leaves = metadata["migration_leaves"]
    if leaves != [list(item) for item in sorted({tuple(item) for item in leaves})]:
        raise ValueError("migration_leaves must be sorted and unique")
    sequence = metadata["schema_sequence"]
    minimum = metadata["minimum_compatible_schema_sequence"]
    safety = metadata["migration_safety"]
    if minimum > sequence:
        raise ValueError("minimum compatible sequence exceeds schema sequence")
    if safety in {"forward-only", "destructive"} and minimum != sequence:
        raise ValueError("irreversible release must require its own schema sequence")
    if predecessor is None:
        return
    validate_metadata(predecessor, schema)
    if release_order(metadata) <= release_order(predecessor):
        raise ValueError("release order is not strictly increasing")
    changed = leaves != predecessor["migration_leaves"]
    expected = predecessor["schema_sequence"] + int(changed)
    if sequence != expected:
        raise ValueError("schema sequence does not match migration leaf change")
    if changed and safety == "no-schema-change":
        raise ValueError("changed migration leaves require migration safety")
    if not changed and minimum != predecessor["minimum_compatible_schema_sequence"]:
        raise ValueError("no-schema-change release must preserve compatibility floor")


def migration_leaves(project: Path) -> list[list[str]]:
    command = [sys.executable, "manage.py", "showmigrations", "--plan"]
    result = subprocess.run(command, cwd=project, check=True, text=True, capture_output=True)
    applied: dict[str, str] = {}
    for line in result.stdout.splitlines():
        match = re.search(r"\[X\]\s+([\w.]+)\.([\w]+)", line)
        if match:
            applied[match.group(1)] = match.group(2)
    return [[app, migration] for app, migration in sorted(applied.items())]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, required=True)
    parser.add_argument("--schema", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--created-at", required=True)
    parser.add_argument("--migration-safety", required=True)
    parser.add_argument("--media-storage-mode", required=True)
    parser.add_argument("--static-manifest", type=Path, required=True)
    parser.add_argument("--predecessor", type=Path)
    args = parser.parse_args()
    predecessor = load_json(args.predecessor) if args.predecessor else None
    leaves = migration_leaves(args.project)
    changed = predecessor is not None and leaves != predecessor["migration_leaves"]
    sequence = (predecessor["schema_sequence"] if predecessor else 0) + int(changed)
    minimum = predecessor["minimum_compatible_schema_sequence"] if predecessor else 0
    if args.migration_safety in {"forward-only", "destructive"}:
        minimum = sequence
    timestamp = datetime.fromisoformat(args.created_at.replace("Z", "+00:00"))
    release_id = timestamp.strftime("%Y%m%dT%H%M%SZ") + "-" + args.commit[:12]
    metadata = {
        "schema_version": 1,
        "release_id": release_id,
        "commit": args.commit,
        "created_at": timestamp.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "python_version": ".".join(map(str, sys.version_info[:3])),
        "django_version": importlib.metadata.version("django"),
        "gunicorn_version": importlib.metadata.version("gunicorn"),
        "migration_leaves": leaves,
        "schema_sequence": sequence,
        "minimum_compatible_schema_sequence": minimum,
        "migration_safety": args.migration_safety,
        "media_storage_mode": args.media_storage_mode,
        "static_manifest_sha256": hashlib.sha256(args.static_manifest.read_bytes()).hexdigest(),
    }
    validate_metadata(metadata, load_json(args.schema), predecessor)
    args.output.write_text(json.dumps(metadata, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
