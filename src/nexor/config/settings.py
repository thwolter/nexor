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

    def _postgres_url_with_driver(self, drivername: str) -> SecretStr:
        if self.postgres_url is None:
            raise RuntimeError('postgres_url is required')

        raw_url = self.postgres_url.get_secret_value()
        url = make_url(raw_url)
        if url.get_backend_name() == 'postgresql':
            url = url.set(drivername=drivername)

        return SecretStr(url.render_as_string(hide_password=False))

    @property
    def async_postgres_url(self) -> SecretStr:
        return self._postgres_url_with_driver('postgresql+asyncpg')

    @property
    def sync_postgres_url(self) -> SecretStr:
        return self._postgres_url_with_driver('postgresql+psycopg')
