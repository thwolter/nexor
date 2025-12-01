from pydantic import SecretStr
import pytest

from nexor.config import ServiceSettings


def test_async_postgres_url_normalizes_and_adds_asyncpg_driver():
    settings = ServiceSettings(postgres_url=SecretStr('postgres://reader:secret@localhost/test'))
    assert settings.async_postgres_url.get_secret_value() == 'postgresql+asyncpg://reader:secret@localhost/test'


def test_sync_postgres_url_always_uses_psycopg_driver():
    settings = ServiceSettings(postgres_url=SecretStr('postgresql://reader:secret@localhost/test'))
    assert settings.sync_postgres_url.get_secret_value() == 'postgresql+psycopg://reader:secret@localhost/test'


def test_postgres_url_helpers_require_postgres_url():
    settings = ServiceSettings(postgres_url=SecretStr('postgresql://reader:secret@localhost/test'))
    settings.postgres_url = None
    with pytest.raises(RuntimeError):
        _ = settings.async_postgres_url
    with pytest.raises(RuntimeError):
        _ = settings.sync_postgres_url
