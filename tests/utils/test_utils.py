import tomllib
from pathlib import Path

from nexor.utils import get_app_name, get_app_version, normalize_postgres_url


def test_normalize_postgres_url_upgrades_postgres_scheme():
    assert normalize_postgres_url('postgres://user:pass@localhost/db') == 'postgresql://user:pass@localhost/db'


def test_normalize_postgres_url_leaves_postgresql_scheme_intact_and_unchanged():
    original = 'postgresql://user:pass@localhost/db'
    assert normalize_postgres_url(original) == original


def test_app_version_and_name_match_pyproject():
    path = Path(__file__).resolve().parents[2] / 'pyproject.toml'
    with open(path, 'rb') as f:
        data = tomllib.load(f)

    assert get_app_version() == data['project']['version']
    assert get_app_name() == data['project']['name']


def _write_pyproject(path: Path, name: str, version: str) -> None:
    path.write_text(f'[project]\nname="{name}"\nversion="{version}"\n', encoding='utf-8')


def test_app_identifiers_walk_up_to_parent(monkeypatch, tmp_path):
    root = tmp_path / 'project-root'
    root.mkdir()
    _write_pyproject(root / 'pyproject.toml', 'parent-app', '1.2.3')

    child = root / 'workspace'
    child.mkdir()
    monkeypatch.chdir(child)

    assert get_app_version() == '1.2.3'
    assert get_app_name() == 'parent-app'


def test_app_identifiers_use_env_override(tmp_path, monkeypatch):
    target = tmp_path / 'alternate-root'
    target.mkdir()
    _write_pyproject(target / 'pyproject.toml', 'env-app', '9.9.9')

    monkeypatch.setenv('NEXOR_APP_ROOT', str(target))

    assert get_app_version() == '9.9.9'
    assert get_app_name() == 'env-app'


def test_app_identifiers_fallback_to_unknown_when_pyproject_missing(monkeypatch):
    def fake_open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr('builtins.open', fake_open)

    assert get_app_version() == 'unknown'
    assert get_app_name() == 'unknown'
