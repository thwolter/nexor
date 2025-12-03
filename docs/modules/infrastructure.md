# `nexor.infrastructure`

## Overview

The `nexor.infrastructure.db` helpers standardise async SQLAlchemy/SQLModel engine creation and session management.
They rely on the shared `ServiceSettings` to normalise `postgres_url` before switching to `postgresql+asyncpg`.
Caching is keyed by the running event loop plus DSN so concurrent FastAPI workers reuse the same pooled engines.

| Helper | Responsibility |
| --- | --- |
| `get_engine` | Return or create a cached `AsyncEngine` for `settings.async_postgres_url`. |
| `session_factory` | Async context manager yielding a session; handles rollback on exception. |
| `scoped_session` | Wraps `tenauth.access_scoped_session_ctx` for tenant-aware session scopes. |
| `pg_connect` / `pg_connection` | Lightweight asyncpg helpers for raw `asyncpg.Connection`. |
| `test_db_connection` | Attempts repeated connections via `dispose_engines`/`get_engine` to validate readiness. |

## Example

```python
from nexor.infrastructure import db
from nexor.config import ServiceSettings


async def fetch_count(settings: ServiceSettings) -> int:
    async with db.session_factory(settings=settings) as session:
        result = await session.execute('SELECT count(*) FROM some_table')
        return result.scalar_one()
```

Use `db.scoped_session` when an `AccessContext` is available, and rely on `test_db_connection` inside the `/healthz` route described in [Health](modules/health.md).

## API Reference

::: nexor.infrastructure.db
