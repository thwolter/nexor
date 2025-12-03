# `nexor.utils`

## Overview

Utility helpers underpin the configuration validation and fingerprinting behaviour used across the package.
They also allow services to derive metadata such as the package name or version without repeating TOML parsing logic.

| Helper | Description |
| --- | --- |
| `parse_cors_origins` | Normalises environment-specified CORS origins supplied as JSON, CSV or single strings. |
| `ValidatedSettings` | BaseSettings subclass that enforces `required_keys` via `_check_missing_keys`. |
| `ValidatedModel` | BaseModel counterpart that issues warnings rather than raising when required fields are absent. |
| `FingerprintMixin` | Adds deterministic fingerprinting to Pydantic models using selected include/exclude sets. |
| `normalize_postgres_url` | Converts `postgres://` URLs to `postgresql://`. |
| `get_app_name`, `get_app_version` | Read the `project.name`/`project.version` values from the nearest `pyproject.toml`. |

## Example

```python
from nexor.utils import FingerprintMixin


class RequestBody(FingerprintMixin):
    fingerprint_keys = ['user_id', 'payload']

    user_id: int
    payload: dict


request = RequestBody(user_id=42, payload={'foo': 'bar'})
print(request.get_fingerprint())
```

The fingerprint helper ensures deterministic hashes even when dictionary keys reorder, thanks to JSON dumping with sorted keys.

## API Reference

::: nexor.utils
