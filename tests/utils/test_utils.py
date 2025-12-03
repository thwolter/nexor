import tomllib
from pathlib import Path

from nexor.utils import app_name, app_version, normalize_postgres_url


def test_normalize_postgres_url_upgrades_postgres_scheme():
    assert normalize_postgres_url('postgres://user:pass@localhost/db') == 'postgresql://user:pass@localhost/db'


def test_normalize_postgres_url_leaves_postgresql_scheme_intact_and_unchanged():
    original = 'postgresql://user:pass@localhost/db'
    assert normalize_postgres_url(original) == original


def test_app_version_and_name_match_pyproject():
    path = Path(__file__).resolve().parents[2] / 'pyproject.toml'
    with open(path, 'rb') as f:
        data = tomllib.load(f)

    assert app_version() == data['project']['version']
    assert app_name() == data['project']['name']


def test_app_identifiers_fallback_to_unknown_when_pyproject_missing(monkeypatch):
    def fake_open(*args, **kwargs):
        raise FileNotFoundError

    monkeypatch.setattr('builtins.open', fake_open)

    assert app_version() == 'unknown'
    assert app_name() == 'unknown'
