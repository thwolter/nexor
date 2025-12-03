# `nexor.health`

## Overview

`install_health_routes` wires `/healthz`, `/readyz` and `/readyz/worker` endpoints into a FastAPI application,
using the shared database helpers to verify connectivity and allowing a custom worker ping callback for background processes.

| Endpoint | Behaviour |
| --- | --- |
| `/healthz` | Runs `nexor.infrastructure.db.test_db_connection` to confirm the database is reachable. |
| `/readyz` | Always returns `{'status': 'ready'}` for generic readiness gating. |
| `/readyz/worker` | Calls the supplied `worker_ping` and raises a `503` if it fails. |

## Example

```python
from fastapi import FastAPI

from myproject.settings import settings
from nexor.health import install_health_routes

app = FastAPI()
install_health_routes(app, settings=settings, prefix='/health', enabled=True)
```

Pass `worker_ping` when background queues or processes have their own health semantics.

## API Reference

::: nexor.health.install_health_routes
