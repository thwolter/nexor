# `nexor.config`

## Overview

`ServiceSettings` is a lightweight base class built on `nexor.utils.ValidatedSettings`.
It centralises the most frequent settings required by FDE services and ensures that critical keys such as
`postgres_url` are present and uniformly normalised.

| Feature | Description |
| --- | --- |
| Required keys | `ServiceSettings.required_keys` defaults to `['postgres_url']` and can be extended by subclasses. |
| URL normalisation | Both `postgres_url` and `alembic_url` are normalised to `postgresql://` using `normalize_postgres_url`. |
| Helpers | `async_postgres_url` and `migration_url` provide driver-swapped versions suitable for asyncpg and Alembic respectively. |
| Metadata | `env`, `version`, `debug`, `app_schema` and pooling knobs are all configurable, keeping the environment signal consistent. |

## Example

```python
from pydantic import SecretStr

from nexor.config import ServiceSettings


class Settings(ServiceSettings):
    postgres_url: SecretStr
    alembic_url: SecretStr
    debug: bool = True

settings = Settings()
print(settings.async_postgres_url)
```

This configuration ensures that your service inherits the standard lifecycle and validation for shared database helpers. See [Quickstart](../quickstart.md) for how it ties into the rest of Nexor.

## API Reference

::: nexor.config.settings.ServiceSettings
