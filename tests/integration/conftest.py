import pytest
from pydantic import SecretStr
from testcontainers.postgres import PostgresContainer

from nexor.config import NexorDBSettings

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
def db_settings(postgres_url) -> NexorDBSettings:
    """Return settings configured to talk to the test Postgres instance."""
    return NexorDBSettings(
        postgres_url=postgres_url,
        alembic_url=postgres_url,
        app_schema='integration',
    )
