from pathlib import Path

import django
from packaging.version import Version


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_project_uses_uv_only_not_poetry():
    assert not (PROJECT_ROOT / "poetry.lock").exists()

    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8").lower()
    assert "poetry" not in pyproject


def test_django_version_is_current_stable_6_0_line():
    version = Version(django.get_version())

    assert version.major == 6
    assert version.minor == 0
    assert not version.is_prerelease
    assert not version.is_devrelease
