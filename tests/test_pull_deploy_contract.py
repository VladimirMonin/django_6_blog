import re
from pathlib import Path
import subprocess

import yaml

ROOT = Path(__file__).parents[1]


def test_pull_workflow_is_closed_exact_sha_contract():
    path = ROOT / ".github/workflows/deploy.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    triggers = workflow.get("on") or workflow.get(True)
    assert set(triggers) == {"push", "workflow_dispatch"}
    assert triggers["push"] == {"tags": ["v*"]}
    deploy = workflow["jobs"]["deploy"]
    assert deploy["runs-on"] == "ubuntu-latest"
    assert deploy["needs"] == "verify"
    assert deploy["environment"] == "production"
    assert deploy["permissions"] == {"contents": "read", "deployments": "write"}
    text = path.read_text(encoding="utf-8")
    assert "timeweb-pull-v1" in text
    assert "repos/$REPOSITORY/deployments" in text
    assert "deployments/$DEPLOYMENT_ID/statuses" in text
    assert "https://exception-blog.ru/_deploy/status" in text
    assert "self-hosted" not in text
    assert "DEPLOY_SSH" not in text
    assert not re.findall(r"secrets\.([A-Z0-9_]+)", text)


def test_checkout_adapter_is_fixed_origin_exact_sha_boundary():
    adapter = ROOT / "deploy/host/django-6-blog-checkout-deploy"
    text = adapter.read_text(encoding="utf-8")
    assert "https://github.com/VladimirMonin/django_6_blog.git" in text
    assert '[[ "$commit" =~ ^[a-f0-9]{40}$ ]]' in text
    assert "status --porcelain --untracked-files=no" in text
    assert "merge-base --is-ancestor" in text
    assert "http.version=HTTP/1.1" in text
    assert "for attempt in $(seq 1 5)" in text
    assert "flock -n" in text
    assert "EnvironmentFile=$env_file" in text
    assert "manage.py check --deploy" in text
    assert "manage.py migrate --noinput" in text
    assert "manage.py collectstatic --noinput" in text
    assert "/api/v1/health/ready/" in text
    assert "--resolve exception-blog.ru:443:127.0.0.1" in text
    assert "eval " not in text
    subprocess.run(["bash", "-n", str(adapter)], check=True)
    invalid = subprocess.run([str(adapter), "not-a-commit"], text=True, capture_output=True)
    assert invalid.returncode == 2
    assert "invalid commit" in invalid.stderr


def test_poller_is_idempotent_atomic_transport_boundary():
    poller = ROOT / "deploy/host/django-6-blog-deployment-poller"
    text = poller.read_text(encoding="utf-8")
    compile(text, str(poller), "exec")
    assert "api.github.com/repos/VladimirMonin/django_6_blog/" in text
    assert 'TRANSPORT = "timeweb-pull-v1"' in text
    assert "fcntl.LOCK_EX | fcntl.LOCK_NB" in text
    assert "last-deployment-id" in text
    assert "deployment-status.json" in text
    assert 'ADAPTER = Path("/usr/local/sbin/django-6-blog-checkout-deploy")' in text
    assert "os.replace(temporary, path)" in text

    timer = (ROOT / "deploy/systemd/django-6-blog-deployment-poller.timer").read_text(encoding="utf-8")
    service = (ROOT / "deploy/systemd/django-6-blog-deployment-poller.service").read_text(encoding="utf-8")
    assert "OnUnitActiveSec=2min" in timer and "Persistent=true" in timer
    assert "User=root" in service
    assert "ExecStart=/usr/local/sbin/django-6-blog-deployment-poller" in service


def test_nginx_exposes_only_read_only_deployment_status():
    nginx = (ROOT / "deploy/nginx/django-6-blog.conf.example").read_text(encoding="utf-8")
    assert "location = /_deploy/status" in nginx
    assert "/var/lib/django-6-blog/deployment-status.json" in nginx
    assert 'add_header Cache-Control "no-store"' in nginx
