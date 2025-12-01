import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Tuple
from uuid import UUID

import asyncpg
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from tenauth.schemas import AccessContext
from tenauth.session import access_scoped_session_ctx

from nexor.config.settings import ServiceSettings

logger = logging.getLogger(__name__)

Loop = asyncio.AbstractEventLoop
SessionFactory = async_sessionmaker[AsyncSession]

_engine_cache: dict[Tuple[Loop, str], AsyncEngine] = {}
_sessionmaker_cache: dict[Tuple[Loop, str], SessionFactory] = {}

DB_CONNECTION_TEST_RETRIES = 3


def _current_loop() -> Loop:
    try:
        return asyncio.get_running_loop()
    except RuntimeError as exc:
        raise RuntimeError('A running event loop is required to access the async engine') from exc


def _cache_key(loop: Loop, url: str) -> Tuple[Loop, str]:
    return loop, url


def _normalize_async_url(settings: ServiceSettings) -> str:
    return settings.async_postgres_url.get_secret_value()


def get_engine(settings: ServiceSettings, *, connect_args: dict = None) -> AsyncEngine:
    loop = _current_loop()

    url = _normalize_async_url(settings)
    key = _cache_key(loop, url)
    engine = _engine_cache.get(key)
    if engine is None:
        engine = create_async_engine(
            url,
            echo=settings.debug or False,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_timeout=settings.db_pool_timeout,
            connect_args=connect_args,
        )
        _engine_cache[key] = engine
    return engine


def _get_sessionmaker(settings: ServiceSettings, *, connect_args: dict = None) -> SessionFactory:
    loop = _current_loop()
    url = _normalize_async_url(settings)
    key = _cache_key(loop, url)
    sessionmaker = _sessionmaker_cache.get(key)
    if sessionmaker is None:
        sessionmaker = async_sessionmaker(
            bind=get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
            connect_args=connect_args,
        )
        _sessionmaker_cache[key] = sessionmaker
    return sessionmaker


@asynccontextmanager
async def session_factory(settings: ServiceSettings, *, connect_args: dict = None) -> AsyncIterator[AsyncSession]:
    session = _get_sessionmaker(settings, connect_args)()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


@asynccontextmanager
async def scoped_session(
    *,
    settings: ServiceSettings,
    access_context: AccessContext,
    verify: bool = True,
    connect_args: dict = None,
) -> AsyncIterator[AsyncSession]:
    async with access_scoped_session_ctx(
        session_factory=lambda: session_factory(settings, connect_args=connect_args),
        access_context=access_context,
        verify=verify,
    ) as session:
        exc: Exception | None = None
        try:
            yield session
        except Exception as err:
            exc = err
            raise
        finally:
            if exc is None:
                await session.commit()


async def pg_connect(postgres_url: SecretStr, tenant_id: UUID | None) -> asyncpg.Connection:
    dsn = postgres_url.get_secret_value()
    dsn = dsn.replace('+asyncpg://', '://', 1)
    if tenant_id is None:
        return await asyncpg.connect(dsn=dsn)
    return await asyncpg.connect(dsn=dsn, server_settings={'app.tenant_id': str(tenant_id)})


@asynccontextmanager
async def pg_connection(
    postgres_url: SecretStr,
    tenant_id: UUID | None,
) -> AsyncIterator[asyncpg.Connection]:
    conn = await pg_connect(postgres_url, tenant_id)
    try:
        yield conn
    finally:
        await conn.close()


async def dispose_engines(*, loop: Loop | None = None) -> None:
    if loop is None:
        try:
            loop = _current_loop()
        except RuntimeError:
            return

    to_dispose = [key for key in _engine_cache if key[0] is loop]
    for key in to_dispose:
        engine = _engine_cache.pop(key, None)
        _sessionmaker_cache.pop(key, None)
        if engine is not None:
            await engine.dispose()


def _retry_connection_after_dispose(max_attempts: int):
    if max_attempts < 1:
        raise ValueError('max_attempts must be at least 1')

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exc: Exception | None = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as exc:
                    last_exc = exc
                    if attempt >= max_attempts:
                        raise
                    await dispose_engines()
            assert last_exc is not None
            return None

        return wrapper

    return decorator


@_retry_connection_after_dispose(DB_CONNECTION_TEST_RETRIES)
async def _test_db_connection_once(settings: ServiceSettings) -> None:
    engine = get_engine(settings)
    logger.info(engine.url.render_as_string(hide_password=False))
    async with engine.connect():
        pass


async def test_db_connection(settings: ServiceSettings) -> None:
    try:
        await _test_db_connection_once(settings)
        logger.info('Database connection test successful')
    except Exception as exc:
        logger.exception('Database connection test failed')
        await dispose_engines()
        raise RuntimeError('Failed to connect to database') from exc
