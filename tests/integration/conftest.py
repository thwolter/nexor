import pytest
from pydantic import SecretStr
from testcontainers.postgres import PostgresContainer

from nexor.config.settings import ServiceSettings

POSTGRES_IMAGE = 'postgres:16-alpine'


@pytest.fixture(scope='session')
def postgres_container():
    """Provide a PostgreSQL container for the integration tests."""
    container = PostgresContainer(POSTGRES_IMAGE)
    container.start()
    try:
        yield container
    finally:
        container.stop()


@pytest.fixture(scope='session')
def postgres_url(postgres_container) -> SecretStr:
    """Expose the DSN for the running Postgres instance."""
    return SecretStr(postgres_container.get_connection_url())


@pytest.fixture(scope='session')
def db_settings(postgres_url) -> ServiceSettings:
    """Return settings configured to talk to the test Postgres instance."""
    return ServiceSettings(postgres_url=postgres_url)
