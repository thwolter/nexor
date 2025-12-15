# Nexor

Reusable configuration and database helpers for the FDE services.

## Goals
- Centralize the async SQLAlchemy/SQLModel engine, session, and `asyncpg` helpers so every service can share the same connection lifecycle.
- Provide a lightweight `ServiceSettings` base plus the `ValidatedSettings`/`ValidatedModel` helpers so each service uses consistent validation for environment variables.
- Provide shared logging and observability helpers (`nexor.logging.configure_loguru_logging`, `nexor.logging.configure_std_logging`, `nexor.observability.*`) so every service uses consistent console sinks, OTLP exporters, and resource attributes.

## Installation
Install the package via a path dependency (see harvestor `pyproject.toml` for an example):

```bash
pip install -e ../nexor
```

or add `nexor @ file://../nexor` to your project's `[project].dependencies`.

## Usage
### Shared configuration
Customize your service settings by inheriting from `nexor.config.ServiceSettings` (exported as `ServiceSettings` for backward compatibility). Each instance exposes a `.db` attribute backed by `NexorDBSettings`, so database helpers receive a focused configuration object:

```python
from pydantic import Field, SecretStr

from nexor.config import NexorDBSettings, ServiceSettings


class Settings(ServiceSettings):
    required_keys = ['redis_url', 'openai_api_key']
    debug: bool | None = None
    redis_url: SecretStr | None = None
    db: NexorDBSettings = Field(default_factory=lambda: NexorDBSettings(app_schema='my-service'))
```

`nexor.config` also exports `normalize_postgres_url` so each service can canonicalize a URL once per process. `Settings.db` provides `async_postgres_url`, `migration_url`, pooling knobs, and schema defaults that every service shares.

### Database helpers
Call the shared session helpers with your service settings:

```python
from nexor.infrastructure import db
from config import get_settings

get_engine = db.get_engine(get_settings().db)

async with db.session_factory(get_settings().db) as session:
    ...
```

Use `db.scoped_session(db_settings=settings.db, access_context=access)` when tenant-scoped sessions are required, and leverage `db.test_db_connection(settings.db)` during startup health checks.
