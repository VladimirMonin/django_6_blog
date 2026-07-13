"""Проверки offline-контракта backup/restore через поддельные утилиты."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import subprocess
import tarfile

import pytest

ROOT = Path(__file__).parents[1]
RUN_BACKUP = ROOT / "scripts/backup/run-backup.sh"


def executable(path: Path, content: str) -> None:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + content, encoding="utf-8")
    path.chmod(0o755)


def fake_tools(tmp_path: Path) -> Path:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    executable(bindir / "pg_dump", 'if [[ "${1:-}" == "--version" ]]; then echo "pg_dump (PostgreSQL) 16.4"; exit; fi\n[[ "${FAKE_FAIL_TOOL:-}" == pg_dump ]] && exit 8\nfor arg in "$@"; do [[ "$arg" == --file=* ]] && printf dump > "${arg#--file=}"; done\n')
    executable(
        bindir / "pg_restore",
        '[[ "${1:-}" == "--version" ]] && { echo "pg_restore (PostgreSQL) 16.4"; exit; }; '
        '[[ "${FAKE_FAIL_TOOL:-}" == pg_restore ]] && exit 8; '
        'for arg in "$@"; do [[ "$arg" == --list ]] && exit 0; done; '
        'if [[ -n "${FAKE_WRITE_LOG:-}" ]]; then printf "pg_restore\\n" >> "$FAKE_WRITE_LOG"; fi; exit 0\n',
    )
    executable(bindir / "age", '[[ "${1:-}" == "--version" ]] && { echo "age 1.2.0"; exit; }; [[ "${FAKE_FAIL_TOOL:-}" == age ]] && exit 8; out=""; input=""; while (($#)); do case "$1" in --output) out=$2; shift 2;; --recipient|--identity) shift 2;; --decrypt) shift;; *) input=$1; shift;; esac; done; if [[ -n "$input" ]]; then cp "$input" "$out"; else cat > "$out"; fi\n')
    executable(bindir / "flock", '[[ "${1:-}" == "--version" ]] && { echo "flock from util-linux 2.39.0"; exit; }; exit 0\n')
    executable(bindir / "rclone", '[[ "${1:-}" == "--version" ]] && { echo "rclone v1.68.0"; exit; }; op=$1; shift; [[ "${FAKE_FAIL_TOOL:-}" == "rclone:$op" ]] && exit 8; case "$op" in copy) if [[ "$2" = /* ]]; then mkdir -p "$2"; if [[ -d "$1" ]]; then cp -a "$1/." "$2/"; else printf media > "$2/object"; fi; fi; if [[ -n "${FAKE_WRITE_LOG:-}" ]]; then printf "media-copy\\n" >> "$FAKE_WRITE_LOG"; fi;; copyto) mkdir -p "$(dirname "$2")"; cp "$1" "$2";; rcat) mkdir -p "$(dirname "$1")"; cat > "$1";; lsf) printf "%s" "${RESTORE_MEDIA_LIST:-}";; *) exit 9;; esac\n')
    executable(bindir / "psql", 'printf "%s\\n" "${RESTORE_DB_COUNT:-0}"\n')
    return bindir


def backup_env(tmp_path: Path, bindir: Path) -> dict[str, str]:
    root = tmp_path / "offline"
    media = tmp_path / "media-source"
    media.mkdir()
    (media / "object").write_text("media")
    return {
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "BACKUP_OFFLINE_ROOT": str(root),
        "BACKUP_STATE_DIR": str(root / "state"),
        "BACKUP_SCRATCH_DIR": str(root / "scratch"),
        "BACKUP_EVIDENCE_DIR": str(root / "evidence"),
        "BACKUP_LOCK_FILE": str(root / "lock" / "backup.lock"),
        "BACKUP_SOURCE_PG_MAJOR": "16",
        "BACKUP_EXECUTION_MODE": "fake",
        "BACKUP_AGE_RECIPIENT": "age1offline",
        "BACKUP_MEDIA_SOURCE": str(media),
        "BACKUP_MEDIA_DESTINATION": str(root / "remote"),
        "BACKUP_ID_OVERRIDE": "20260712T120000Z-test",
    }


def test_backup_refuses_missing_environment_without_side_effects(tmp_path):
    result = subprocess.run(
        ["bash", str(RUN_BACKUP)],
        env={"PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert list(tmp_path.iterdir()) == []


def test_backup_orchestrates_encrypted_artifacts_manifest_success_and_state(tmp_path):
    bindir = fake_tools(tmp_path)
    env = backup_env(tmp_path, bindir)
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    root = Path(env["BACKUP_OFFLINE_ROOT"])
    backup_id = env["BACKUP_ID_OVERRIDE"]
    remote = root / "remote" / backup_id
    assert {path.name for path in remote.iterdir()} == {
        "SUCCESS", "checksums.sha256", "manifest.json", "media.tar.age", "postgres.dump.age"
    }
    assert (remote / "SUCCESS").read_text().strip() == backup_id
    manifest = json.loads((remote / "manifest.json").read_text())
    assert manifest == {"schema_version": 1, "backup_id": backup_id, "status": "verified", "source_pg_major": 16}
    assert (root / "state" / "last-success").read_text().strip() == backup_id
    assert not (root / "scratch" / backup_id).exists()


def test_tool_version_boundary_fails_before_backup_directories(tmp_path):
    bindir = fake_tools(tmp_path)
    executable(bindir / "age", '[[ "${1:-}" == "--version" ]] && { echo "age 2.0.0"; exit; }; exit 0\n')
    env = backup_env(tmp_path, bindir)
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    root = Path(env["BACKUP_OFFLINE_ROOT"])
    assert not (root / "state").exists()
    assert not (root / "remote").exists()


def test_restore_descriptor_refuses_permissive_mode(tmp_path):
    target = tmp_path / "target.json"
    target.write_text("{}")
    target.chmod(0o644)
    result = subprocess.run(
        [str(ROOT / "scripts/restore/verify-restored-state.py"), str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "unsafe target file" in result.stderr


def test_disposable_restore_descriptor_is_emitted_from_single_validated_read(tmp_path):
    target = tmp_path / "target.json"
    descriptor = {
        "schema_version": 1,
        "target_kind": "disposable",
        "target_id": "restore-test",
        "database_name": "restore_test",
        "media_prefix": "restore-test/media",
        "expected_database_empty": True,
        "expected_media_empty": True,
        "maintenance_marker": "/run/django-6-blog/restore-maintenance/restore-test",
    }
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    result = subprocess.run(
        [str(ROOT / "scripts/restore/verify-restored-state.py"), "--emit-json", str(target)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout) == descriptor


def test_restore_descriptor_identity_mutation_is_refused(tmp_path):
    target = tmp_path / "target.json"
    snapshot = tmp_path / "snapshot.json"
    descriptor = {
        "schema_version": 1,
        "target_kind": "disposable",
        "target_id": "restore-test",
        "database_name": "restore_test",
        "media_prefix": "restore-test/media",
        "expected_database_empty": True,
        "expected_media_empty": True,
        "maintenance_marker": "/run/django-6-blog/restore-maintenance/restore-test",
    }
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    verifier = ROOT / "scripts/restore/verify-restored-state.py"
    first = subprocess.run([str(verifier), "--snapshot", str(snapshot), str(target)], capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(descriptor))
    replacement.chmod(0o600)
    replacement.replace(target)
    second = subprocess.run([str(verifier), "--revalidate", str(snapshot), str(target)], capture_output=True, text=True)
    assert second.returncode != 0
    assert "target identity changed" in second.stderr


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("schema_version", 2),
        ("target_kind", "other"),
        ("target_id", "Bad_ID"),
        ("database_name", "bad-name"),
        ("media_prefix", "../escape"),
        ("expected_database_empty", False),
        ("expected_media_empty", False),
        ("maintenance_marker", "/tmp/marker"),
    ],
)
def test_restore_descriptor_schema_matrix_refuses_unsafe_values(tmp_path, field, value):
    _, target, descriptor, _, _ = _restore_fixture(tmp_path)
    descriptor[field] = value
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    result = subprocess.run(
        [str(ROOT / "scripts/restore/verify-restored-state.py"), str(target)],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0


def test_restore_descriptor_refuses_extra_field_symlink_and_missing_production_marker(tmp_path):
    _, target, descriptor, _, _ = _restore_fixture(tmp_path)
    descriptor["extra"] = "no"
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    verifier = ROOT / "scripts/restore/verify-restored-state.py"
    extra = subprocess.run([str(verifier), str(target)], text=True, capture_output=True)
    assert extra.returncode != 0
    real = tmp_path / "real.json"
    descriptor.pop("extra")
    real.write_text(json.dumps(descriptor))
    real.chmod(0o600)
    target.unlink()
    target.symlink_to(real)
    symlink = subprocess.run([str(verifier), str(target)], text=True, capture_output=True)
    assert symlink.returncode != 0
    target.unlink()
    descriptor["target_kind"] = "production"
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    marker = subprocess.run([str(verifier), str(target)], text=True, capture_output=True)
    assert marker.returncode != 0
    assert "maintenance marker" in marker.stderr


@pytest.mark.parametrize(
    ("tool", "version", "supported"),
    [
        ("age", "1.1.9", False), ("age", "1.2.0", True), ("age", "1.99.99", True), ("age", "2.0.0", False),
        ("rclone", "1.67.9", False), ("rclone", "1.68.0", True), ("rclone", "1.99.99", True), ("rclone", "2.0.0", False),
        ("flock", "2.38.9", False), ("flock", "2.39.0", True), ("flock", "2.99.99", True), ("flock", "3.0.0", False),
    ],
)
def test_tool_version_finite_boundaries(tmp_path, tool, version, supported):
    bindir = fake_tools(tmp_path)
    prefixes = {"age": "age ", "rclone": "rclone v", "flock": "flock from util-linux "}
    executable(bindir / tool, f'[[ "${{1:-}}" == "--version" ]] && {{ echo "{prefixes[tool]}{version}"; exit; }}; exit 0\n')
    env = backup_env(tmp_path, bindir)
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    if supported:
        assert "unsupported" not in result.stderr
        assert Path(env["BACKUP_STATE_DIR"]).exists()
    else:
        assert result.returncode != 0
        assert not Path(env["BACKUP_STATE_DIR"]).exists()


@pytest.mark.parametrize(
    ("tool", "output"),
    [
        ("age", "nonsense"),
        ("age", "age 1.2.0 extra"),
        ("rclone", "rclone v1.68.0 extra"),
        ("flock", "flock from util-linux 2.39.0 extra"),
    ],
)
def test_malformed_tool_versions_refuse_before_state(tmp_path, tool, output):
    bindir = fake_tools(tmp_path)
    executable(bindir / tool, f'echo {shlex.quote(output)}\n')
    env = backup_env(tmp_path, bindir)
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert not Path(env["BACKUP_STATE_DIR"]).exists()


@pytest.mark.parametrize("major", ["16", "17", "18"])
def test_postgresql_supported_major_matrix(tmp_path, major):
    bindir = fake_tools(tmp_path)
    for tool in ("pg_dump", "pg_restore"):
        body = f'[[ "${{1:-}}" == "--version" ]] && {{ echo "{tool} (PostgreSQL) {major}.9"; exit; }}; '
        if tool == "pg_dump":
            body += 'for arg in "$@"; do [[ "$arg" == --file=* ]] && printf dump > "${arg#--file=}"; done\n'
        else:
            body += "exit 0\n"
        executable(bindir / tool, body)
    env = backup_env(tmp_path, bindir)
    env["BACKUP_SOURCE_PG_MAJOR"] = major
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("dump_version", "restore_version", "source_major"),
    [
        ("15.9", "15.9", "15"),
        ("19.0", "19.0", "19"),
        ("16.9", "17.1", "16"),
        ("16.9", "16.9", "17"),
        ("nonsense", "16.9", "16"),
        ("16.9", "nonsense", "16"),
    ],
)
def test_postgresql_unsupported_malformed_and_mismatch_refuse_before_state(
    tmp_path, dump_version, restore_version, source_major
):
    bindir = fake_tools(tmp_path)
    executable(bindir / "pg_dump", f'echo "pg_dump (PostgreSQL) {dump_version}"\n')
    executable(bindir / "pg_restore", f'echo "pg_restore (PostgreSQL) {restore_version}"\n')
    env = backup_env(tmp_path, bindir)
    env["BACKUP_SOURCE_PG_MAJOR"] = source_major
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    assert not Path(env["BACKUP_STATE_DIR"]).exists()
    assert not (Path(env["BACKUP_OFFLINE_ROOT"]) / "remote").exists()


@pytest.mark.parametrize("failure", ["pg_dump", "pg_restore", "age", "rclone:copy", "rclone:copyto", "rclone:rcat"])
def test_backup_phase_failure_never_publishes_success_or_last_success(tmp_path, failure):
    bindir = fake_tools(tmp_path)
    env = backup_env(tmp_path, bindir)
    env["FAKE_FAIL_TOOL"] = failure
    env["CANARY_SECRET"] = "canary-never-print"
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode != 0
    root = Path(env["BACKUP_OFFLINE_ROOT"])
    assert not (root / "state/last-success").exists()
    if (root / "remote").exists():
        assert not list((root / "remote").glob("*/SUCCESS"))
    assert "canary-never-print" not in result.stdout + result.stderr


def test_backup_lock_refusal_precedes_work_and_success_marker(tmp_path):
    bindir = fake_tools(tmp_path)
    executable(bindir / "flock", '[[ "${1:-}" == "--version" ]] && { echo "flock from util-linux 2.39.0"; exit; }; exit 1\n')
    env = backup_env(tmp_path, bindir)
    result = subprocess.run(["bash", str(RUN_BACKUP)], env=env, capture_output=True, text=True)
    assert result.returncode == 3
    root = Path(env["BACKUP_OFFLINE_ROOT"])
    assert not (root / "state/last-success").exists()
    assert not (root / "remote").exists()


def _restore_fixture(tmp_path: Path):
    bindir = fake_tools(tmp_path)
    backup_id = "20260713T120000Z-test"
    remote = tmp_path / "remote" / backup_id
    remote.mkdir(parents=True)
    (remote / "postgres.dump.age").write_text("postgres")
    media_tree = tmp_path / "media-tree"
    media_tree.mkdir()
    (media_tree / "object").write_text("media")
    with tarfile.open(remote / "media.tar.age", "w") as archive:
        archive.add(media_tree / "object", arcname="object")
    (remote / "manifest.json").write_text(
        json.dumps({"schema_version": 1, "backup_id": backup_id, "status": "verified", "source_pg_major": 16})
    )
    with (remote / "checksums.sha256").open("w") as checksums:
        subprocess.run(
            ["sha256sum", "postgres.dump.age", "media.tar.age", "manifest.json"],
            cwd=remote,
            text=True,
            stdout=checksums,
            check=True,
        )
    (remote / "SUCCESS").write_text(backup_id + "\n")
    target = tmp_path / "target.json"
    descriptor = {
        "schema_version": 1,
        "target_kind": "disposable",
        "target_id": "restore-test",
        "database_name": "restore_test",
        "media_prefix": "restore-test/media",
        "expected_database_empty": True,
        "expected_media_empty": True,
        "maintenance_marker": "/run/django-6-blog/restore-maintenance/restore-test",
    }
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    write_log = tmp_path / "writes.log"
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "BACKUP_MEDIA_DESTINATION": str(tmp_path / "remote"),
        "RESTORE_AGE_IDENTITY_FILE": str(tmp_path / "identity"),
        "RESTORE_SCRATCH_DIR": str(tmp_path / "scratch"),
        "RESTORE_EXECUTION_MODE": "fake",
        "FAKE_WRITE_LOG": str(write_log),
    }
    return backup_id, target, descriptor, env, write_log


def _run_in_tty(
    command: list[str],
    phrase: str,
    env: dict[str, str],
    *,
    pass_fds: tuple[int, ...] = (),
):
    return subprocess.run(
        ["script", "-qefc", shlex.join(command), "/dev/null"],
        env=env,
        pass_fds=pass_fds,
        input=phrase + "\n",
        text=True,
        capture_output=True,
    )


def test_disposable_restore_executes_through_owned_entry_point(tmp_path):
    backup_id, target, _, env, write_log = _restore_fixture(tmp_path)
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert write_log.read_text().splitlines() == ["pg_restore", "media-copy"]


def test_restore_descriptor_mutation_after_validation_causes_zero_writes(tmp_path):
    backup_id, target, descriptor, env, write_log = _restore_fixture(tmp_path)
    replacement = tmp_path / "replacement.json"
    replacement.write_text(json.dumps(descriptor))
    replacement.chmod(0o600)
    env["RESTORE_TEST_REPLACE_TARGET_WITH"] = str(replacement)
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode != 0
    assert "target identity changed" in result.stdout + result.stderr
    assert not write_log.exists()


def test_restore_descriptor_mutation_during_final_empty_check_causes_zero_writes(tmp_path):
    backup_id, target, descriptor, env, write_log = _restore_fixture(tmp_path)
    replacement = tmp_path / "replacement-during-empty-check.json"
    replacement.write_text(json.dumps(descriptor))
    replacement.chmod(0o600)
    bindir = Path(env["PATH"].split(":", 1)[0])
    executable(
        bindir / "psql",
        'cp -- "$RESTORE_TEST_REPLACEMENT" "$RESTORE_TARGET_FILE"\n'
        'chmod 0600 "$RESTORE_TARGET_FILE"\n'
        'printf "0\\n"\n',
    )
    env.update(
        {
            "RESTORE_TEST_REPLACEMENT": str(replacement),
            "RESTORE_TARGET_FILE": str(target),
        }
    )
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode != 0
    assert "target identity changed" in result.stdout + result.stderr
    assert not write_log.exists()


def test_restore_descriptor_mutation_during_pg_restore_preflight_causes_zero_writes(tmp_path):
    backup_id, target, descriptor, env, write_log = _restore_fixture(tmp_path)
    replacement = tmp_path / "replacement-during-pg-restore.json"
    replacement.write_text(json.dumps(descriptor))
    replacement.chmod(0o600)
    bindir = Path(env["PATH"].split(":", 1)[0])
    executable(
        bindir / "pg_restore",
        '[[ "${1:-}" == "--version" ]] && { echo "pg_restore (PostgreSQL) 16.4"; exit; };\n'
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == --list ]]; then\n'
        '    cp -- "$RESTORE_TEST_REPLACEMENT" "$RESTORE_TARGET_FILE"\n'
        '    chmod 0600 "$RESTORE_TARGET_FILE"\n'
        '    exit 0\n'
        '  fi\n'
        'done\n'
        'printf "pg_restore\\n" >> "$FAKE_WRITE_LOG"\n',
    )
    env.update(
        {
            "RESTORE_TEST_REPLACEMENT": str(replacement),
            "RESTORE_TARGET_FILE": str(target),
        }
    )
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode != 0
    assert "target identity changed" in result.stdout + result.stderr
    assert not write_log.exists()


def test_production_restore_marker_mutation_during_final_empty_check_causes_zero_writes(tmp_path):
    _, target, descriptor, _, _ = _restore_fixture(tmp_path)
    fake_run = tmp_path / "fake-run"
    marker = fake_run / "django-6-blog/restore-maintenance/production-test"
    marker.parent.mkdir(parents=True)
    marker.write_text("production-test")
    marker.chmod(0o600)
    replacement = tmp_path / "replacement-marker"
    replacement.write_text("production-test")
    replacement.chmod(0o600)
    descriptor.update(
        {
            "target_kind": "production",
            "target_id": "production-test",
            "database_name": "production_test",
            "media_prefix": "production-test/media",
            "maintenance_marker": "/run/django-6-blog/restore-maintenance/production-test",
        }
    )
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    descriptor_fd = os.open(target, os.O_RDONLY)
    marker_fd = os.open(marker, os.O_RDONLY)

    def mapped_identity(fd: int):
        details = os.fstat(fd)
        return {
            "device": details.st_dev,
            "inode": details.st_ino,
            "mode": details.st_mode,
            "uid": 0,
            "size": details.st_size,
            "mtime_ns": details.st_mtime_ns,
        }

    snapshot = {
        "descriptor": mapped_identity(descriptor_fd),
        "marker": mapped_identity(marker_fd),
        "target": descriptor,
    }
    replacement.replace(marker)
    write_log = tmp_path / "writes.log"
    env = {
        **os.environ,
        "RESTORE_IDENTITY_SNAPSHOT_JSON": json.dumps(snapshot, separators=(",", ":")),
        "RESTORE_DESCRIPTOR_FD": str(descriptor_fd),
        "RESTORE_MARKER_FD": str(marker_fd),
    }
    command = (
        f"mount --bind {shlex.quote(str(fake_run))} /run && "
        f"exec {shlex.quote(str(ROOT / 'scripts/restore/verify-restored-state.py'))} "
        f"--revalidate-held {shlex.quote(str(target))}"
    )
    try:
        result = subprocess.run(
            ["unshare", "-Urmp", "sh", "-c", command],
            env=env,
            pass_fds=(descriptor_fd, marker_fd),
            text=True,
            capture_output=True,
        )
    finally:
        os.close(descriptor_fd)
        os.close(marker_fd)
    assert result.returncode != 0
    assert "target identity changed" in result.stdout + result.stderr
    assert not write_log.exists()


def test_production_marker_mutation_during_pg_restore_preflight_causes_zero_writes(tmp_path):
    backup_id, target, descriptor, env, write_log = _restore_fixture(tmp_path)
    marker = tmp_path / "production-test.marker"
    marker.write_text("production-test")
    marker.chmod(0o600)
    replacement = tmp_path / "replacement-marker-during-pg-restore"
    replacement.write_text("production-test")
    replacement.chmod(0o600)
    descriptor.update(
        {
            "target_kind": "production",
            "target_id": "production-test",
            "database_name": "production_test",
            "media_prefix": "production-test/media",
            "maintenance_marker": str(marker),
        }
    )
    target.write_text(json.dumps(descriptor))
    target.chmod(0o600)
    bindir = Path(env["PATH"].split(":", 1)[0])
    executable(
        bindir / "pg_restore",
        '[[ "${1:-}" == "--version" ]] && { echo "pg_restore (PostgreSQL) 16.4"; exit; };\n'
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == --list ]]; then\n'
        '    cp -- "$RESTORE_TEST_MARKER_REPLACEMENT" "$RESTORE_TEST_MARKER_PATH"\n'
        '    chmod 0600 "$RESTORE_TEST_MARKER_PATH"\n'
        '    exit 0\n'
        '  fi\n'
        'done\n'
        'printf "pg_restore\\n" >> "$FAKE_WRITE_LOG"\n',
    )
    env["RESTORE_TEST_MARKER_REPLACEMENT"] = str(replacement)
    env["RESTORE_TEST_MARKER_PATH"] = str(marker)
    descriptor_fd = os.open(target, os.O_RDONLY)
    marker_fd = os.open(marker, os.O_RDONLY)

    def held_identity(fd: int):
        details = os.fstat(fd)
        return {
            "device": details.st_dev,
            "inode": details.st_ino,
            "mode": details.st_mode,
            "uid": details.st_uid,
            "size": details.st_size,
            "mtime_ns": details.st_mtime_ns,
        }

    snapshot = {
        "descriptor": held_identity(descriptor_fd),
        "marker": held_identity(marker_fd),
        "target": descriptor,
    }
    env.update(
        {
            "RESTORE_REQUIRED_KIND": "production",
            "RESTORE_DESCRIPTOR_JSON": json.dumps(descriptor, separators=(",", ":")),
            "RESTORE_IDENTITY_SNAPSHOT_JSON": json.dumps(snapshot, separators=(",", ":")),
            "RESTORE_DESCRIPTOR_FD": str(descriptor_fd),
            "RESTORE_MARKER_FD": str(marker_fd),
        }
    )
    try:
        result = _run_in_tty(
            [str(ROOT / "scripts/restore/execute-restore.sh"), "unused", str(target), backup_id],
            f"RESTORE PRODUCTION production-test {backup_id}",
            env,
            pass_fds=(descriptor_fd, marker_fd),
        )
    finally:
        os.close(descriptor_fd)
        os.close(marker_fd)
    assert result.returncode != 0
    assert "target identity changed" in result.stdout + result.stderr
    assert not write_log.exists()


@pytest.mark.parametrize(("db_count", "media_list"), [("1", ""), ("0", "object\n")])
def test_restore_nonempty_targets_refuse_before_writes(tmp_path, db_count, media_list):
    backup_id, target, _, env, write_log = _restore_fixture(tmp_path)
    env.update({"RESTORE_DB_COUNT": db_count, "RESTORE_MEDIA_LIST": media_list})
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode != 0
    assert not write_log.exists()


@pytest.mark.parametrize("source_major", [15, 17, 19, "bad"])
def test_restore_client_source_major_mismatch_refuses_before_writes(tmp_path, source_major):
    backup_id, target, _, env, write_log = _restore_fixture(tmp_path)
    manifest = Path(env["BACKUP_MEDIA_DESTINATION"]) / backup_id / "manifest.json"
    data = json.loads(manifest.read_text())
    data["source_pg_major"] = source_major
    manifest.write_text(json.dumps(data))
    remote = manifest.parent
    with (remote / "checksums.sha256").open("w") as checksums:
        subprocess.run(
            ["sha256sum", "postgres.dump.age", "media.tar.age", "manifest.json"],
            cwd=remote,
            text=True,
            stdout=checksums,
            check=True,
        )
    result = _run_in_tty(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode != 0
    assert not write_log.exists()


def test_restore_refuses_non_tty_and_wrong_entry_point_before_download(tmp_path):
    backup_id, target, _, env, write_log = _restore_fixture(tmp_path)
    direct = subprocess.run(
        [str(ROOT / "scripts/restore/rehearse-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        env=env,
        text=True,
        capture_output=True,
    )
    assert direct.returncode != 0
    wrong = subprocess.run(
        [str(ROOT / "scripts/restore/production-restore.sh"), "--target-file", str(target), "--backup-id", backup_id],
        env=env,
        text=True,
        capture_output=True,
    )
    assert wrong.returncode != 0
    assert "does not own target kind" in wrong.stderr
    assert not write_log.exists()


def test_restore_dry_run_validates_backup_and_targets_without_writes(tmp_path):
    backup_id, target, _, env, write_log = _restore_fixture(tmp_path)
    result = _run_in_tty(
        [
            str(ROOT / "scripts/restore/rehearse-restore.sh"),
            "--dry-run",
            "--target-file",
            str(target),
            "--backup-id",
            backup_id,
        ],
        f"RESTORE DISPOSABLE restore-test {backup_id}",
        env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "validated (dry run)" in result.stdout
    assert not write_log.exists()


def _prune_fixture(tmp_path: Path):
    bindir = tmp_path / "prune-bin"
    bindir.mkdir()
    calls = tmp_path / "lsf-calls"
    purge_log = tmp_path / "purge.log"
    executable(
        bindir / "rclone",
        'op=$1; shift\ncase "$op" in\n'
        f'lsf) count=0; [[ -f {shlex.quote(str(calls))} ]] && count=$(cat {shlex.quote(str(calls))}); count=$((count+1)); printf "%s" "$count" > {shlex.quote(str(calls))}; '
        'if [[ "${PRUNE_RACE:-0}" == 1 && "$count" -gt 1 ]]; then printf "20260713T120000Z-other/\\n"; else printf "20260713T120000Z-test/\\n"; fi;;\n'
        f'purge) printf "%s\\n" "$1" >> {shlex.quote(str(purge_log))};;\n'
        '*) exit 9;; esac\n',
    )
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "BACKUP_MEDIA_DESTINATION": "remote:backups",
    }
    return env, purge_log


def test_prune_dry_run_and_non_tty_execute_delete_nothing(tmp_path):
    env, purge_log = _prune_fixture(tmp_path)
    dry = subprocess.run(
        [str(ROOT / "scripts/backup/prune-backups.sh"), "--dry-run"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert dry.returncode == 0
    refused = subprocess.run(
        [str(ROOT / "scripts/backup/prune-backups.sh"), "--execute"],
        env=env,
        text=True,
        capture_output=True,
    )
    assert refused.returncode != 0
    assert not purge_log.exists()


def test_prune_exact_tty_confirmation_deletes_only_selected_backup(tmp_path):
    env, purge_log = _prune_fixture(tmp_path)
    result = _run_in_tty(
        [str(ROOT / "scripts/backup/prune-backups.sh"), "--execute"],
        "PRUNE 20260713T120000Z-test 1",
        env,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert purge_log.read_text().strip() == "remote:backups/20260713T120000Z-test"


@pytest.mark.parametrize("phrase", ["PRUNE 20260713T120000Z-test 2", "yes", ""])
def test_prune_bad_confirmation_refuses_before_delete(tmp_path, phrase):
    env, purge_log = _prune_fixture(tmp_path)
    result = _run_in_tty(
        [str(ROOT / "scripts/backup/prune-backups.sh"), "--execute"],
        phrase,
        env,
    )
    assert result.returncode != 0
    assert not purge_log.exists()


def test_prune_manifest_digest_race_refuses_before_delete(tmp_path):
    env, purge_log = _prune_fixture(tmp_path)
    env["PRUNE_RACE"] = "1"
    result = _run_in_tty(
        [str(ROOT / "scripts/backup/prune-backups.sh"), "--execute"],
        "PRUNE 20260713T120000Z-test 1",
        env,
    )
    assert result.returncode != 0
    assert "candidate manifest changed" in result.stdout + result.stderr
    assert not purge_log.exists()
