# `nexor.config`

## Overview

`ServiceSettings` is a lightweight base class built on `nexor.utils.ValidatedSettings`.
It exposes a `.db` attribute backed by `NexorDBSettings`, which centralises the Postgres URL, schema, Alembic URL, and pooling knobs so every service shares the same database contract.

| Feature | Description |
| --- | --- |
| Required keys | `NexorDBSettings.required_keys` defaults to `['postgres_url']` and can be extended by consumers with nested `required_keys`. |
| URL normalisation | `NexorDBSettings` normalises both `postgres_url` and `alembic_url` to `postgresql://` via `normalize_postgres_url`. |
| Helpers | `settings.db.async_postgres_url` and `settings.db.migration_url` provide driver-swapped versions suitable for asyncpg and Alembic respectively. |
| Metadata | `env`, `version`, `debug`, and observability flags live on `ServiceSettings`, while schema defaults remain on `NexorDBSettings`. |

## Example

```python
from nexor.config import NexorDBSettings, ServiceSettings


class Settings(ServiceSettings):
    db: NexorDBSettings = NexorDBSettings(app_schema='my-service')


settings = Settings()
print(settings.db.async_postgres_url)
```

This configuration ensures that your service inherits the standard lifecycle and validation for shared database helpers. See [Quickstart](../quickstart.md) for how it ties into the rest of Nexor.

## API Reference

::: nexor.config.settings.ServiceSettings
