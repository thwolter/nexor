from typing import Awaitable, Callable, TypeVar

from fastapi import APIRouter, FastAPI, HTTPException

from nexor.config.settings import ServiceSettings
from nexor.infrastructure.db import test_db_connection

S = TypeVar('S', bound=ServiceSettings)


async def _noop_worker_ping() -> None:
    """Default worker ping that does nothing."""
    return None


def install_health_routes(
    app: FastAPI,
    *,
    settings: S,
    prefix: str = '/health',
    enabled: bool = True,
    worker_ping: Callable[[], Awaitable[None]] = _noop_worker_ping,
) -> None:
    """
    Install health-related routes into the given FastAPI app.

    Parameters:
        app: FastAPI application into which the routes are injected
        settings: application settings
        prefix: route prefix (customisable by the installing backend)
        enabled: installing backend may disable these routes
        worker_ping: callable that performs a healthcheck on the worker
    """
    if not enabled:
        return

    router = APIRouter(prefix=prefix, tags=['health'])

    @router.get('/healthz')
    async def healthz():  # pragma: no cover - lightweight healthcheck
        try:
            await test_db_connection(settings)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {'status': 'ok'}

    @router.get('/readyz')
    async def readyz():  # pragma: no cover - trivial endpoint
        return {'status': 'ready'}

    @router.get('/readyz/worker')
    async def readyz_worker():  # pragma: no cover - lightweight healthcheck
        try:
            await worker_ping()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=str(exc))
        return {'status': 'ready'}

    app.include_router(router)
