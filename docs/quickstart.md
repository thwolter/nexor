# Quickstart

This quickstart demonstrates how to bring together the core Nexor helpers to ship a FastAPI service with consistent configuration, telemetry and health checks.

## 1. Define service settings

```python
from nexor.config import NexorDBSettings, ServiceSettings


class Settings(ServiceSettings):
    required_keys = ['redis_url']
    redis_url: str
    db: NexorDBSettings = NexorDBSettings(app_schema='my-service')


settings = Settings()
```

This derives from `nexor.config.ServiceSettings` so the environment validation, normalization and async/sync URLs remain consistent across services. Refer to [Configuration](modules/config.md) for field details.

## 2. Initialise logging and tracing

```python
from nexor.logging import configure_loguru_logging, LogExporterSettings
from nexor.observability import init_observability

configure_loguru_logging(
    settings=settings,
    exporter_settings=LogExporterSettings(enabled=True, service_name='my-service'),
)

init_observability(service_name='my-service')
```

This installs both Loguru and optional OTLP graphing so downstream services ingest a shared trace/resource schema. See [logging](modules/logging.md) and [observability](modules/observability.md) for the knobs exposed to tune exporters.

## 3. Use the shared database helpers

```python
from fastapi import FastAPI

from nexor.health import install_health_routes
from nexor.infrastructure import db

app = FastAPI()
install_health_routes(app, settings=settings)


@app.get('/')
async def home():
    async with db.session_factory(db_settings=settings.db) as session:
        result = await session.execute('SELECT 1')
        return {'result': result.scalar_one()}
```

The `db` helpers provide cached engines, scoped sessions and asynchronous connection contexts that mirror the lifecycle used across FDE services. `install_health_routes` wires simple `/healthz`, `/readyz` and `/readyz/worker` endpoints so the service can signal readiness; refer to [Health](modules/health.md) for details.

## 4. Run the service

```bash
uv run uvicorn my_service:app --reload
```

This assumes an `uv`-managed environment and lets uvicorn pick up the shared settings. For production deployments, omit `--reload` and ensure the `postgres_url`/`redis_url` are set.

TODO: add service-specific extras (e.g. migrations) when more guidance exists.
