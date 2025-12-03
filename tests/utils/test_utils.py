from nexor.utils import normalize_postgres_url


def test_normalize_postgres_url_upgrades_postgres_scheme():
    assert normalize_postgres_url('postgres://user:pass@localhost/db') == 'postgresql://user:pass@localhost/db'


def test_normalize_postgres_url_leaves_postgresql_scheme_intact_and_unchanged():
    original = 'postgresql://user:pass@localhost/db'
    assert normalize_postgres_url(original) == original
