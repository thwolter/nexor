from typing import Literal

from pydantic import SecretStr, field_validator
from sqlalchemy.engine import make_url

from nexor.utils import ValidatedSettings, normalize_postgres_url


class ServiceSettings(ValidatedSettings):
    """Lightweight base settings for database-backed services."""

    required_keys = ['postgres_url']

    env: Literal['development', 'production', 'testing'] = 'production'
    debug: bool | None = None
    postgres_url: SecretStr | None = None
    alembic_url: SecretStr | None = None
    app_schema: str = 'nexor'
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    @field_validator('postgres_url', mode='before')
    @classmethod
    def _normalize_postgres_url(cls, url: SecretStr | None) -> str | None:
        if url is None:
            return None
        return normalize_postgres_url(url.get_secret_value())

    @field_validator('alembic_url', mode='before')
    @classmethod
    def _normalize_alembic_url(cls, url: SecretStr | None) -> str | None:
        if url is None:
            return None
        return normalize_postgres_url(url.get_secret_value())

    @property
    def async_postgres_url(self) -> SecretStr:
        if self.postgres_url is None:
            raise RuntimeError('postgres_url must be provided to build async_postgres_url')
        url = make_url(self.postgres_url.get_secret_value())
        url = url.set(drivername='postgresql+asyncpg')
        return SecretStr(url.render_as_string(hide_password=False))

    @property
    def migration_url(self) -> SecretStr:
        if self.alembic_url is None:
            raise RuntimeError('alembic_url must be provided to build migration_url')
        url = make_url(self.alembic_url.get_secret_value())
        url = url.set(drivername='postgresql+psycopg')
        return SecretStr(url.render_as_string(hide_password=False))
