import pytest
from pydantic import SecretStr

from nexor.config import DatabaseSettings, ServiceSettings


class SettingsWithDB(ServiceSettings):
    db: DatabaseSettings


def _make_db_settings(**overrides) -> DatabaseSettings:
    """Provide a consistent NexorDBSettings instance for testing."""
    defaults = {
        'postgres_url': SecretStr('postgres://reader:secret@localhost/test'),
        'alembic_url': SecretStr('postgres://reader:secret@localhost/test'),
        'app_schema': 'test',
    }
    defaults.update(overrides)
    return DatabaseSettings(**defaults)


def test_async_postgres_url_normalizes_and_adds_asyncpg_driver():
    settings = SettingsWithDB(db=_make_db_settings())
    assert settings.db.async_postgres_url.get_secret_value() == 'postgresql+asyncpg://reader:secret@localhost/test'


def test_migration_url_always_uses_psycopg_driver():
    settings = SettingsWithDB(
        db=_make_db_settings(
            alembic_url=SecretStr('postgresql://reader:secret@localhost/test'),
            postgres_url=SecretStr('...'),
        )
    )
    assert settings.db.migration_url.get_secret_value() == 'postgresql+psycopg://reader:secret@localhost/test'


def test_postgres_url_helpers_require_postgres_url():
    settings = SettingsWithDB(db=_make_db_settings())
    settings.db.__dict__['postgres_url'] = None
    settings.db.__dict__['alembic_url'] = None
    with pytest.raises(RuntimeError):
        _ = settings.db.async_postgres_url
    with pytest.raises(RuntimeError):
        _ = settings.db.migration_url
