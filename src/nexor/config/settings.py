import warnings
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings
from sqlalchemy.engine import make_url

from nexor.utils import ValidatedSettings, get_app_version, normalize_postgres_url


class DatabaseSettings(BaseSettings):
    postgres_url: SecretStr
    alembic_url: SecretStr
    app_schema: str
    debug: bool | None = False
    db_pool_size: int = 20
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    @field_validator('postgres_url', mode='before')
    @classmethod
    def _normalize_postgres_url(cls, url: str | SecretStr | None) -> SecretStr | None:
        if url is None:
            return None
        if isinstance(url, SecretStr):
            url = url.get_secret_value()
        normalized_url = normalize_postgres_url(url)
        return SecretStr(normalized_url)

    @field_validator('alembic_url', mode='before')
    @classmethod
    def _normalize_alembic_url(cls, url: str | SecretStr | None) -> SecretStr | None:
        if url is None:
            return None
        if isinstance(url, SecretStr):
            url = url.get_secret_value()
        normalized_url = normalize_postgres_url(url)
        return SecretStr(normalized_url)

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

    @field_validator('app_schema')
    @classmethod
    def _lowercase_schema(cls, value: str) -> str:
        return value.lower()

    @field_validator('debug', mode='before')
    @classmethod
    def _coerce_debug(cls, value: bool | None) -> bool | None:
        return value or False


class NexorDBSettings(DatabaseSettings):
    def __init__(self, **data):
        warnings.warn(
            'NexorDBSettings is deprecated and will be removed in a future version. Use DatabaseSettings instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)


class ServiceSettings(ValidatedSettings):
    """Lightweight base settings for database-backed services."""

    env: Literal['development', 'production', 'testing'] = 'production'
    version: str = Field(default_factory=get_app_version)
    debug: bool | None = None

    def __init__(self, **data):
        warnings.warn(
            'ServiceSettings is deprecated and will be removed in a future version. Use DatabaseSettings instead.',
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**data)
