import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import textwrap

import pytest
import py_compile
import yaml

from jsonschema import Draft202012Validator

ROOT = Path(__file__).parents[1]


def test_shell_artifacts_parse():
    for path in ROOT.glob("scripts/**/*.sh"):
        subprocess.run(["bash", "-n", str(path)], check=True)


def test_release_metadata_schema_is_closed():
    schema = json.loads((ROOT / "deploy/release-metadata.schema.json").read_text())
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False


def test_host_artifacts_keep_trusted_boundaries():
    nginx = (ROOT / "deploy/nginx/django-6-blog.conf.example").read_text()
    assert "proxy_set_header Host $host" in nginx
    assert "proxy_intercept_errors off" in nginx
    assert "unix:/run/django-6-blog/gunicorn.sock" in nginx
    assert "location = /_deploy/status" in nginx
    assert "/var/lib/django-6-blog/deployment-status.json" in nginx
    unit = (ROOT / "deploy/systemd/django-6-blog-maintenance@.service").read_text()
    assert "EnvironmentFile=/etc/django-6-blog/" in unit
    assert "User=django-blog" in unit and "sh -c" not in unit


def _metadata(release_id, created_at, commit, *, sequence=0, minimum=0, safety="no-schema-change", storage="filesystem"):
    return {
        "schema_version": 1,
        "release_id": release_id,
        "commit": commit,
        "created_at": created_at,
        "python_version": "3.12.0",
        "django_version": "6.0.5",
        "gunicorn_version": "23.0.0",
        "migration_leaves": [["blog", f"00{sequence + 1}_initial"]],
        "schema_sequence": sequence,
        "minimum_compatible_schema_sequence": minimum,
        "migration_safety": safety,
        "media_storage_mode": storage,
        "static_manifest_sha256": "a" * 64,
    }


def _fake_release(root, name, metadata):
    release = root / "releases" / name
    python = release / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    python.symlink_to(Path(os.sys.executable))
    (release / "scripts" / "deploy").mkdir(parents=True)
    shutil.copy(ROOT / "scripts/deploy/release_metadata.py", release / "scripts/deploy/release_metadata.py")
    shutil.copy(ROOT / "scripts/deploy/rollback_verdict.py", release / "scripts/deploy/rollback_verdict.py")
    (release / "deploy").mkdir()
    shutil.copy(ROOT / "deploy/release-metadata.schema.json", release / "deploy/release-metadata.schema.json")
    (release / "release-metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return release


def test_rollback_atomically_selects_compatible_older_release(tmp_path):
    current = _fake_release(tmp_path, "new", _metadata("20260712T120000Z-" + "b" * 12, "2026-07-12T12:00:00Z", "b" * 40))
    target = _fake_release(tmp_path, "old", _metadata("20260711T120000Z-" + "a" * 12, "2026-07-11T12:00:00Z", "a" * 40))
    (tmp_path / "current").symlink_to(current)
    leaves = tmp_path / "leaves.json"
    leaves.write_text(json.dumps(json.loads((current / "release-metadata.json").read_text())["migration_leaves"]))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/deploy/rollback.sh")],
        env={**os.environ, "RELEASE_ROOT": str(tmp_path), "TARGET_RELEASE": "old", "SKIP_READINESS": "1", "LIVE_MIGRATION_LEAVES_FILE": str(leaves)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert "ALLOW_CODE_STATIC_ONLY" in result.stdout
    assert (tmp_path / "current").resolve() == target


def test_rollback_refuses_schema_too_old_before_irreversible_boundary(tmp_path):
    current = _fake_release(tmp_path, "new", _metadata("20260712T120000Z-" + "b" * 12, "2026-07-12T12:00:00Z", "b" * 40, sequence=2, minimum=2, safety="forward-only"))
    _fake_release(tmp_path, "old", _metadata("20260711T120000Z-" + "a" * 12, "2026-07-11T12:00:00Z", "a" * 40, sequence=1))
    (tmp_path / "current").symlink_to(current)
    leaves = tmp_path / "leaves.json"
    leaves.write_text(json.dumps(json.loads((current / "release-metadata.json").read_text())["migration_leaves"]))
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/deploy/rollback.sh")],
        env={**os.environ, "RELEASE_ROOT": str(tmp_path), "TARGET_RELEASE": "old", "SKIP_READINESS": "1", "LIVE_MIGRATION_LEAVES_FILE": str(leaves)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 3
    assert "REFUSE_SCHEMA_TOO_OLD" in result.stdout
    assert (tmp_path / "current").resolve() == current


def test_socket_and_service_share_the_same_runtime_socket():
    socket = (ROOT / "deploy/systemd/django-6-blog.socket").read_text()
    service = (ROOT / "deploy/systemd/django-6-blog.service").read_text()
    gunicorn = (ROOT / "deploy/gunicorn.conf.py").read_text()
    assert "ListenStream=/run/django-6-blog/gunicorn.sock" in socket
    assert "RuntimeDirectory=django-6-blog" in service
    assert "unix:/run/django-6-blog/gunicorn.sock" in gunicorn


def test_maintenance_wrapper_builds_allowlisted_final_release_argv(tmp_path):
    release_id = "20260712T120000Z-" + "a" * 12
    release = tmp_path / "releases" / release_id
    python = release / ".venv" / "bin" / "python"
    python.parent.mkdir(parents=True)
    log = tmp_path / "argv.json"
    python.write_text(
        "#!/usr/bin/env python3\nimport json, os, sys\n"
        "json.dump({'argv': sys.argv[1:], 'canary': os.environ.get('CANARY')}, open(os.environ['ARGV_LOG'], 'w'))\n"
    )
    python.chmod(0o755)
    (release / "manage.py").write_text("# fake\n")
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/deploy/maintenance.sh"), f"collectstatic:{release_id}"],
        env={**os.environ, "RELEASE_ROOT": str(tmp_path), "ARGV_LOG": str(log), "CANARY": "never-print-me"},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(log.read_text())["argv"] == [str(release / "manage.py"), "collectstatic", "--noinput"]
    assert "never-print-me" not in result.stdout + result.stderr


def test_maintenance_wrapper_refuses_unknown_operation_before_execution(tmp_path):
    result = subprocess.run(
        ["bash", str(ROOT / "scripts/deploy/maintenance.sh"), "shell:unsafe"],
        env={**os.environ, "RELEASE_ROOT": str(tmp_path)},
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2
    assert not (tmp_path / "releases").exists()


def _executable(path: Path, content: str) -> None:
    path.write_text("#!/usr/bin/env bash\nset -euo pipefail\n" + content, encoding="utf-8")
    path.chmod(0o755)


def _release_fixture(tmp_path: Path, *, gunicorn_fails: bool = False):
    release_root = tmp_path / "release-root"
    source = tmp_path / "source"
    bindir = tmp_path / "bin"
    source.mkdir()
    bindir.mkdir()
    (source / "manage.py").write_text(
        textwrap.dedent(
            """
            import os, pathlib, sys
            if sys.argv[1:] == ["collectstatic", "--noinput"]:
                root = pathlib.Path.cwd() / "staticfiles"
                root.mkdir()
                (root / "staticfiles.json").write_text("{}")
            """
        ),
        encoding="utf-8",
    )
    (source / "config").mkdir()
    (source / "config/wsgi.py").write_text("application = None\n", encoding="utf-8")
    (source / "deploy").mkdir()
    (source / "deploy/gunicorn.conf.py").write_text("bind = 'unix:/tmp/fake.sock'\n", encoding="utf-8")
    shutil.copy(ROOT / "deploy/release-metadata.schema.json", source / "deploy/release-metadata.schema.json")
    (source / "scripts/deploy").mkdir(parents=True)
    (source / "scripts/deploy/release_metadata.py").write_text(
        textwrap.dedent(
            """
            import argparse, json, os
            parser = argparse.ArgumentParser()
            for name in ("project", "schema", "output", "commit", "created_at", "migration_safety", "media_storage_mode", "static_manifest", "predecessor"):
                parser.add_argument("--" + name.replace("_", "-"))
            args = parser.parse_args()
            json.dump({"release_id": os.environ["RELEASE_ID"]}, open(args.output, "w"))
            """
        ),
        encoding="utf-8",
    )
    _executable(
        bindir / "uv",
        textwrap.dedent(
            f"""
            [[ "$1" == sync ]]
            mkdir -p .venv/bin
            ln -s {sys.executable!s} .venv/bin/python
            final_python="$PWD/.venv/bin/python"
            cat > .venv/bin/gunicorn <<'EOF'
            #!FINAL_RELEASE_PYTHON
            import os, pathlib, sys
            pathlib.Path(os.environ['GUNICORN_LOG']).write_text(sys.executable)
            raise SystemExit({1 if gunicorn_fails else 0})
            EOF
            sed -i "s|FINAL_RELEASE_PYTHON|$final_python|" .venv/bin/gunicorn
            chmod +x .venv/bin/gunicorn
            """
        ),
    )
    _executable(bindir / "curl", "exit 1\n")
    env = {
        **os.environ,
        "PATH": f"{bindir}:{os.environ['PATH']}",
        "RELEASE_ROOT": str(release_root),
        "SOURCE_DIR": str(source),
        "RELEASE_ID": "20260713T120000Z-" + "a" * 12,
        "RELEASE_COMMIT": "a" * 40,
        "RELEASE_CREATED_AT": "2026-07-13T12:00:00Z",
        "MIGRATION_SAFETY": "no-schema-change",
        "MEDIA_STORAGE_MODE": "s3",
        "GUNICORN_LOG": str(tmp_path / "gunicorn.checked"),
    }
    return release_root, source, env


def _run_release(env: dict[str, str]):
    return subprocess.run(
        ["bash", str(ROOT / "scripts/deploy/release.sh")],
        env=env,
        text=True,
        capture_output=True,
    )


def test_release_executes_successfully_at_final_path_and_preserves_source(tmp_path):
    release_root, source, env = _release_fixture(tmp_path)
    source_sentinel = source / "source-sentinel"
    source_sentinel.write_text("source")
    result = _run_release({**env, "SKIP_READINESS": "1"})
    assert result.returncode == 0, result.stderr
    release = release_root / "releases" / env["RELEASE_ID"]
    final_python = release / ".venv/bin/python"
    shebang = (release / ".venv/bin/gunicorn").read_text().splitlines()[0]
    assert (release_root / "current").resolve() == release
    assert shebang == f"#!{final_python}"
    assert ".incoming-" not in shebang
    assert str(ROOT / ".venv") not in shebang
    assert Path(env["GUNICORN_LOG"]).read_text() == str(final_python)
    assert source_sentinel.read_text() == "source"


def test_release_pre_cutover_failure_keeps_previous_and_source(tmp_path):
    release_root, source, env = _release_fixture(tmp_path, gunicorn_fails=True)
    previous = release_root / "releases/previous"
    previous.mkdir(parents=True)
    (previous / "sentinel").write_text("previous")
    (release_root / "current").symlink_to(previous)
    (source / "sentinel").write_text("source")
    result = _run_release({**env, "SKIP_READINESS": "1"})
    assert result.returncode != 0
    assert (release_root / "current").resolve() == previous
    assert (previous / "sentinel").read_text() == "previous"
    assert (source / "sentinel").read_text() == "source"
    assert not (release_root / "releases" / env["RELEASE_ID"]).exists()


def test_release_post_cutover_failure_restores_previous(tmp_path):
    release_root, source, env = _release_fixture(tmp_path)
    previous = release_root / "releases/previous"
    previous.mkdir(parents=True)
    (previous / "sentinel").write_text("previous")
    (release_root / "current").symlink_to(previous)
    (source / "sentinel").write_text("source")
    result = _run_release({**env, "READINESS_ATTEMPTS": "1"})
    assert result.returncode != 0
    assert (release_root / "current").resolve() == previous
    assert (previous / "sentinel").read_text() == "previous"
    assert (source / "sentinel").read_text() == "source"
    assert not (release_root / "releases" / env["RELEASE_ID"]).exists()


def test_release_refuses_source_static_symlink_without_touching_target(tmp_path):
    release_root, source, env = _release_fixture(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "sentinel"
    sentinel.write_text("outside")
    (source / "staticfiles").symlink_to(outside, target_is_directory=True)
    result = _run_release({**env, "SKIP_READINESS": "1"})
    assert result.returncode != 0
    assert sentinel.read_text() == "outside"
    assert not (release_root / "current").exists()


def test_deploy_workflow_is_closed_tag_or_manual_contract():
    workflow_path = ROOT / ".github/workflows/deploy.yml"
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True)
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"] == {"tags": ["v*"]}
    deploy = workflow["jobs"]["deploy"]
    assert deploy["environment"] == "production"
    assert deploy["runs-on"] == "ubuntu-latest"
    assert deploy["needs"] == "verify"
    assert deploy["permissions"] == {"contents": "read", "deployments": "write"}
    text = workflow_path.read_text(encoding="utf-8")
    assert "timeweb-pull-v1" in text
    assert "repos/$REPOSITORY/deployments" in text
    assert "deployments/$DEPLOYMENT_ID/statuses" in text
    assert "https://exception-blog.ru/_deploy/status" in text
    assert "self-hosted" not in text
    assert "DEPLOY_SSH" not in text
    assert "bash -c" not in text and "sh -c" not in text


def test_checkout_adapter_is_fixed_sha_production_boundary():
    adapter = ROOT / "deploy/host/django-6-blog-checkout-deploy"
    text = adapter.read_text(encoding="utf-8")
    assert "https://github.com/VladimirMonin/django_6_blog.git" in text
    assert '[[ "$commit" =~ ^[a-f0-9]{40}$ ]]' in text
    assert "status --porcelain --untracked-files=no" in text
    assert "merge-base --is-ancestor" in text
    assert "flock -n" in text
    assert "EnvironmentFile=$env_file" in text
    assert "manage.py check --deploy" in text
    assert "manage.py migrate --noinput" in text
    assert "manage.py collectstatic --noinput" in text
    assert "/api/v1/health/ready/" in text
    assert "eval " not in text and f"source {chr(34)}$env_file" not in text
    subprocess.run(["bash", "-n", str(adapter)], check=True)
    result = subprocess.run([str(adapter), "not-a-commit"], text=True, capture_output=True)
    assert result.returncode == 2
    assert "invalid commit" in result.stderr


def test_deployment_poller_is_idempotent_fixed_transport_boundary(tmp_path):
    poller = ROOT / "deploy/host/django-6-blog-deployment-poller"
    text = poller.read_text(encoding="utf-8")
    assert "api.github.com/repos/VladimirMonin/django_6_blog/" in text
    assert 'TRANSPORT = "timeweb-pull-v1"' in text
    assert "fcntl.LOCK_EX | fcntl.LOCK_NB" in text
    assert "last-deployment-id" in text
    assert "deployment-status.json" in text
    assert 'ADAPTER = Path("/usr/local/sbin/django-6-blog-checkout-deploy")' in text
    assert "os.replace(temporary, path)" in text
    py_compile.compile(str(poller), cfile=str(tmp_path / "poller.pyc"), doraise=True)
    timer = (ROOT / "deploy/systemd/django-6-blog-deployment-poller.timer").read_text(encoding="utf-8")
    service = (ROOT / "deploy/systemd/django-6-blog-deployment-poller.service").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=2min" in timer and "Persistent=true" in timer
    assert "User=root" in service
    assert "ExecStart=/usr/local/sbin/django-6-blog-deployment-poller" in service


def test_host_adapter_example_accepts_only_archive_release_id_and_commit():
    adapter = ROOT / "deploy/host/django-6-blog-deploy"
    text = adapter.read_text(encoding="utf-8")
    assert "SSH_ORIGINAL_COMMAND" not in text
    assert "release.tar.gz" not in text
    assert ".adapter-work" in text and 'filter="data"' in text
    assert "repository=/srv/django-6-blog/repository.git" in text
    assert 'archive --format=tar --output="$trusted_archive" "$commit"' in text
    assert 'cmp --silent -- "/proc/self/fd/$archive_fd" "$trusted_archive"' in text
    assert '/usr/sbin/runuser --user "$deploy_user"' in text
    assert '/usr/bin/bash "$source_dir/scripts/deploy/release.sh"' in text
    assert '\n"$source_dir/scripts/deploy/release.sh"' not in text
    subprocess.run(["bash", "-n", str(adapter)], check=True)
    result = subprocess.run([str(adapter), "bad;id", "not-a-commit"], text=True, capture_output=True)
    assert result.returncode == 2


def _host_adapter_fixture(tmp_path: Path):
    source = tmp_path / "source-repository"
    source.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.email", "offline@example.invalid"], cwd=source, check=True)
    subprocess.run(["git", "config", "user.name", "Offline Test"], cwd=source, check=True)
    release_script = source / "scripts/deploy/release.sh"
    release_script.parent.mkdir(parents=True)
    release_script.write_text("#!/usr/bin/env bash\nprintf executed > \"$EXECUTION_LOG\"\n", encoding="utf-8")
    release_script.chmod(0o755)
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=source, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True, capture_output=True, check=True
    ).stdout.strip()
    repository = tmp_path / "repository.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(source), str(repository)], check=True)
    repository.chmod(0o700)
    release_id = "20260713T120000Z-" + commit[:12]
    release_root = tmp_path / "release-root"
    (release_root / "incoming").mkdir(parents=True)
    work_root = release_root / ".adapter-work"
    work_root.mkdir()
    work_root.chmod(0o711)
    adapter = tmp_path / "django-6-blog-deploy"
    text = (ROOT / "deploy/host/django-6-blog-deploy").read_text(encoding="utf-8")
    text = text.replace("release_root=/srv/django-6-blog", f"release_root={shlex.quote(str(release_root))}")
    text = text.replace("repository=/srv/django-6-blog/repository.git", f"repository={shlex.quote(str(repository))}")
    adapter.write_text(text, encoding="utf-8")
    adapter.chmod(0o755)
    return source, release_root, adapter, release_id, commit


def _run_fake_root_adapter(adapter: Path, release_id: str, commit: str, execution_log: Path):
    return subprocess.run(
        ["unshare", "-Ur", str(adapter), release_id, commit],
        env={**os.environ, "EXECUTION_LOG": str(execution_log)},
        text=True,
        capture_output=True,
    )


def test_host_adapter_refuses_forged_archive_before_execution(tmp_path):
    _, release_root, adapter, release_id, commit = _host_adapter_fixture(tmp_path)
    archive = release_root / "incoming" / f"release-{release_id}.tar"
    archive.write_bytes(b"not the authorized commit archive")
    execution_log = tmp_path / "executed"

    result = _run_fake_root_adapter(adapter, release_id, commit, execution_log)

    assert result.returncode != 0
    assert "artifact provenance mismatch" in result.stderr
    assert not execution_log.exists()


def test_host_adapter_refuses_unreachable_commit_before_execution(tmp_path):
    source, release_root, adapter, _, _ = _host_adapter_fixture(tmp_path)
    subprocess.run(["git", "checkout", "-qb", "untrusted"], cwd=source, check=True)
    release_script = source / "scripts/deploy/release.sh"
    release_script.write_text("#!/usr/bin/env bash\nprintf forged > \"$EXECUTION_LOG\"\n", encoding="utf-8")
    subprocess.run(["git", "add", "."], cwd=source, check=True)
    subprocess.run(["git", "commit", "-qm", "untrusted fixture"], cwd=source, check=True)
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=source, text=True, capture_output=True, check=True
    ).stdout.strip()
    release_id = "20260713T120000Z-" + commit[:12]
    archive = release_root / "incoming" / f"release-{release_id}.tar"
    subprocess.run(["git", "archive", "--format=tar", f"--output={archive}", commit], cwd=source, check=True)
    execution_log = tmp_path / "executed"

    result = _run_fake_root_adapter(adapter, release_id, commit, execution_log)

    assert result.returncode != 0
    assert "unauthorized commit" in result.stderr
    assert not execution_log.exists()


def test_host_adapter_refuses_private_archive_replacement_before_execution(tmp_path):
    source, release_root, adapter, release_id, commit = _host_adapter_fixture(tmp_path)
    archive = release_root / "incoming" / f"release-{release_id}.tar"
    subprocess.run(["git", "archive", "--format=tar", f"--output={archive}", commit], cwd=source, check=True)
    replacement = tmp_path / "replacement.tar"
    replacement.write_bytes(archive.read_bytes() + b"replacement")
    text = adapter.read_text(encoding="utf-8")
    text = text.replace(
        'cmp --silent -- "/proc/self/fd/$archive_fd" "$trusted_archive"',
        'cmp --silent -- "/proc/self/fd/$archive_fd" "$trusted_archive"\ncp -- "${ADAPTER_TEST_REPLACEMENT:?}" "$private_archive"',
    )
    adapter.write_text(text, encoding="utf-8")
    execution_log = tmp_path / "executed"
    result = subprocess.run(
        ["unshare", "-Ur", str(adapter), release_id, commit],
        env={
            **os.environ,
            "EXECUTION_LOG": str(execution_log),
            "ADAPTER_TEST_REPLACEMENT": str(replacement),
        },
        text=True,
        capture_output=True,
    )

    assert result.returncode != 0
    assert "private archive identity changed" in result.stderr
    assert not execution_log.exists()


@pytest.mark.parametrize(
    "candidate",
    ["relative", "/", "{root}", "{root}/releases", "{root}/outside", "{outside}/release"],
)
def test_release_path_validator_refuses_unsafe_matrix(tmp_path, candidate):
    release_root = tmp_path / "root"
    outside = tmp_path / "outside"
    candidate = candidate.format(root=release_root, outside=outside)
    script = (
        f"source {shlex.quote(str(ROOT / 'scripts/deploy/lib.sh'))}; "
        f"validate_release {shlex.quote(candidate)}"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        env={**os.environ, "RELEASE_ROOT": str(release_root)},
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0


def test_release_path_validator_refuses_symlink(tmp_path):
    release_root = tmp_path / "root"
    target = release_root / "releases/target"
    target.mkdir(parents=True)
    link = release_root / "releases/link"
    link.symlink_to(target, target_is_directory=True)
    script = (
        f"source {shlex.quote(str(ROOT / 'scripts/deploy/lib.sh'))}; "
        f"validate_release {shlex.quote(str(link))}"
    )
    result = subprocess.run(
        ["bash", "-c", script],
        env={**os.environ, "RELEASE_ROOT": str(release_root)},
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0


def test_deploy_examples_and_workflow_keep_secret_boundary():
    workflow = (ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    assert not re.findall(r"secrets\.([A-Z0-9_]+)", workflow)
    assert "DJANGO_SECRET_KEY" not in workflow
    assert "MEDIA_S3_AUTH_MATERIAL" not in workflow
    production = (ROOT / ".env.production.example").read_text(encoding="utf-8")
    systemd = (ROOT / "deploy/systemd/django-6-blog.env.example").read_text(encoding="utf-8")
    assert "MEDIA_S3_CUSTOM_DOMAIN=\n" in production
    assert "MEDIA_S3_SIGNED_URLS=true" in production
    assert "MEDIA_S3_CUSTOM_DOMAIN=\n" in systemd
    assert "MEDIA_S3_SIGNED_URLS=true" in systemd
    ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env.production" in ignored and ".env.deploy" in ignored


def test_backup_service_has_one_orchestrator_and_timer_never_runs_restore():
    service = (ROOT / "deploy/systemd/django-6-blog-backup.service").read_text(encoding="utf-8")
    timer = (ROOT / "deploy/systemd/django-6-blog-backup.timer").read_text(encoding="utf-8")
    exec_starts = [line for line in service.splitlines() if line.startswith("ExecStart=")]
    assert exec_starts == ["ExecStart=/srv/django-6-blog/current/scripts/backup/run-backup.sh"]
    assert "[Timer]" in timer and "Unit=" not in timer
    assert "restore" not in timer.lower()
