#!/usr/bin/env python3
"""Validate a non-secret restore target descriptor without following symlinks."""

import json
import os
import re
import stat
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Never

REQUIRED = {
    "schema_version", "target_kind", "target_id", "database_name",
    "media_prefix", "expected_database_empty", "expected_media_empty",
    "maintenance_marker",
}
FORBIDDEN_WORDS = ("password", "secret", "token", "credential", "dsn", "endpoint", "access_key")


def fail(message: str) -> Never:
    raise SystemExit(message)


def read_once(path: str):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        fail("unsafe target file")
        raise AssertionError("unreachable")
    stream = os.fdopen(fd, encoding="utf-8")
    details = os.fstat(stream.fileno())
    if not stat.S_ISREG(details.st_mode) or stat.S_IMODE(details.st_mode) != 0o600 or details.st_uid != os.getuid():
        stream.close()
        fail("unsafe target file")
    try:
        return json.load(stream), details, stream
    except (UnicodeDecodeError, json.JSONDecodeError):
        stream.close()
        fail("invalid target schema")


def open_marker(path: Path, target_id: str):
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError:
        fail("unsafe maintenance marker")
    stream = os.fdopen(fd, encoding="utf-8")
    details = os.fstat(stream.fileno())
    try:
        content = stream.read()
    except UnicodeDecodeError:
        stream.close()
        fail("unsafe maintenance marker")
    if not stat.S_ISREG(details.st_mode) or details.st_uid != 0 or stat.S_IMODE(details.st_mode) != 0o600:
        stream.close()
        fail("unsafe maintenance marker")
    if content != target_id:
        stream.close()
        fail("stale maintenance marker")
    return details, stream


def identity(details: os.stat_result) -> dict[str, int]:
    return {
        "device": details.st_dev,
        "inode": details.st_ino,
        "mode": details.st_mode,
        "uid": details.st_uid,
        "size": details.st_size,
        "mtime_ns": details.st_mtime_ns,
    }


def read_held_json(fd: int):
    try:
        os.lseek(fd, 0, os.SEEK_SET)
        with os.fdopen(os.dup(fd), encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        fail("target identity changed")


def path_identity(path: str):
    try:
        return identity(os.stat(path, follow_symlinks=False))
    except OSError:
        fail("target identity changed")


def revalidate_held(path: str):
    try:
        expected = json.loads(os.environ["RESTORE_IDENTITY_SNAPSHOT_JSON"])
        descriptor_fd = int(os.environ["RESTORE_DESCRIPTOR_FD"])
    except (KeyError, ValueError, json.JSONDecodeError):
        fail("invalid held restore authority")
    if identity(os.fstat(descriptor_fd)) != expected["descriptor"]:
        fail("target identity changed")
    if path_identity(path) != expected["descriptor"]:
        fail("target identity changed")
    descriptor = read_held_json(descriptor_fd)
    if descriptor != expected["target"]:
        fail("target identity changed")
    if expected["marker"] is not None:
        try:
            marker_fd = int(os.environ["RESTORE_MARKER_FD"])
        except (KeyError, ValueError):
            fail("invalid held restore authority")
        if identity(os.fstat(marker_fd)) != expected["marker"]:
            fail("target identity changed")
        if path_identity(descriptor["maintenance_marker"]) != expected["marker"]:
            fail("target identity changed")
        try:
            os.lseek(marker_fd, 0, os.SEEK_SET)
            marker_content = os.read(marker_fd, 4096).decode("utf-8")
        except (OSError, UnicodeDecodeError):
            fail("target identity changed")
        if marker_content != descriptor["target_id"]:
            fail("target identity changed")
    print("held restore authority valid")


def exec_with_held_authority(path: str, command: list[str]) -> Never:
    """Replace this verifier with a write command after one final held-authority check."""
    if not command:
        fail("--exec-held requires COMMAND")
    revalidate_held(path)
    try:
        os.execvpe(command[0], command, os.environ)
    except OSError:
        fail("restore write command unavailable")


def validate(data: dict):
    if not isinstance(data, dict) or set(data) != REQUIRED:
        fail("invalid target schema")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        fail("invalid target schema")
    if data["target_kind"] not in {"disposable", "production"}:
        fail("invalid target schema")
    if not isinstance(data["target_id"], str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,62}", data["target_id"]):
        fail("invalid target id")
    if not isinstance(data["database_name"], str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", data["database_name"]):
        fail("invalid database name")
    if not isinstance(data["media_prefix"], str):
        fail("invalid media prefix")
    parts = PurePosixPath(data["media_prefix"]).parts
    if not parts or any(part in {".", "..", ""} for part in parts) or data["media_prefix"].startswith("/"):
        fail("invalid media prefix")
    if data["expected_database_empty"] is not True or data["expected_media_empty"] is not True:
        fail("targets must be empty")
    if not isinstance(data["maintenance_marker"], str):
        fail("invalid maintenance marker")
    marker = Path(data["maintenance_marker"])
    root = Path("/run/django-6-blog/restore-maintenance")
    if not marker.is_absolute() or root not in marker.parents:
        fail("invalid maintenance marker")
    serialized = json.dumps(data).lower()
    if any(word in serialized for word in FORBIDDEN_WORDS):
        fail("target descriptor contains forbidden secret material")
    if data["target_kind"] == "production":
        return open_marker(marker, data["target_id"])
    return None, None


args = sys.argv[1:]
if args[:1] == ["--revalidate-held"]:
    if len(args) != 2:
        fail("--revalidate-held requires TARGET_FILE")
    revalidate_held(args[1])
    raise SystemExit(0)
if args[:1] == ["--exec-held"]:
    try:
        separator = args.index("--", 2)
        exec_target = args[1]
    except (ValueError, IndexError):
        fail("--exec-held requires TARGET_FILE -- COMMAND")
    exec_with_held_authority(exec_target, args[separator + 1:])
hold_exec = None
if "--hold-exec" in args:
    index = args.index("--hold-exec")
    try:
        separator = args.index("--", index + 1)
        hold_target = args[index + 1]
    except (ValueError, IndexError):
        fail("--hold-exec requires -- COMMAND")
    hold_exec = args[separator + 1:]
    args[index:] = [hold_target]
    if not hold_exec:
        fail("--hold-exec requires COMMAND")
emit_json = "--emit-json" in args
snapshot_path = None
revalidate_path = None
if "--snapshot" in args:
    index = args.index("--snapshot")
    snapshot_path = Path(args[index + 1])
    del args[index:index + 2]
if "--revalidate" in args:
    index = args.index("--revalidate")
    revalidate_path = Path(args[index + 1])
    del args[index:index + 2]
if emit_json:
    args.remove("--emit-json")
if len(args) != 1 or (snapshot_path and revalidate_path):
    fail("usage: verify-restored-state.py [--emit-json] [--snapshot FILE|--revalidate FILE] TARGET_FILE")
descriptor, descriptor_stat, descriptor_stream = read_once(args[0])
marker_stat, marker_stream = validate(descriptor)
snapshot = {
    "descriptor": identity(descriptor_stat),
    "marker": identity(marker_stat) if marker_stat else None,
    "target": descriptor,
}
if revalidate_path:
    try:
        expected = json.loads(revalidate_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        fail("invalid identity snapshot")
    if snapshot != expected:
        fail("target identity changed")
if snapshot_path:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(snapshot_path, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(snapshot, stream, separators=(",", ":"))
print(json.dumps(descriptor, separators=(",", ":")) if emit_json else "target descriptor valid")
if hold_exec:
    environment = os.environ.copy()
    environment["RESTORE_DESCRIPTOR_JSON"] = json.dumps(descriptor, separators=(",", ":"))
    environment["RESTORE_IDENTITY_SNAPSHOT_JSON"] = json.dumps(snapshot, separators=(",", ":"))
    environment["RESTORE_DESCRIPTOR_FD"] = str(descriptor_stream.fileno())
    pass_fds = [descriptor_stream.fileno()]
    if marker_stream is not None:
        environment["RESTORE_MARKER_FD"] = str(marker_stream.fileno())
        pass_fds.append(marker_stream.fileno())
    completed = subprocess.run(hold_exec, env=environment, pass_fds=pass_fds, check=False)
    raise SystemExit(completed.returncode)
