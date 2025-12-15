import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import wraps
from typing import Tuple
from uuid import UUID

import asyncpg
from pydantic import SecretStr
from sqlalchemy.engine import make_url
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


def get_engine(settings: ServiceSettings) -> AsyncEngine:
    """
    Creates or retrieves a cached asynchronous database engine.

    This function generates a new asynchronous engine based on the given service
    settings or retrieves a cached one if it already exists, using the specified
    event loop and normalized database URL.

    Args:
        settings (ServiceSettings): The configuration settings for the database
            service, containing parameters required for engine creation such as
            pool size, timeouts, and debug mode.

    Returns:
        AsyncEngine: An asynchronous database engine instance, either newly created
        or fetched from the cache.
    """
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
        )
        _engine_cache[key] = engine
    return engine


def _get_sessionmaker(settings: ServiceSettings) -> SessionFactory:
    loop = _current_loop()
    url = _normalize_async_url(settings)
    key = _cache_key(loop, url)
    sessionmaker = _sessionmaker_cache.get(key)
    if sessionmaker is None:
        sessionmaker = async_sessionmaker(
            bind=get_engine(settings),
            class_=AsyncSession,
            expire_on_commit=False,
        )
        _sessionmaker_cache[key] = sessionmaker
    return sessionmaker


@asynccontextmanager
async def session_factory(settings: ServiceSettings) -> AsyncIterator[AsyncSession]:
    """Creates an asynchronous context manager for managing database sessions.

    This function serves as a factory for generating asynchronous sessions for database
    operations. It yields an active session, handles rollback in case of exceptions, and
    ensures the session is closed after operations are completed.

    Args:
        settings: ServiceSettings instance containing the configuration for creating the
            sessionmaker.

    Yields:
        AsyncSession: An active asynchronous session object for interacting with the database.

    Raises:
        Exception: Propagates any encountered exception after ensuring the session is
            rolled back.
    """
    session = _get_sessionmaker(settings)()
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
) -> AsyncIterator[AsyncSession]:
    """
    Creates a scoped asynchronous database session context.

    This function is an asynchronous context manager for managing a scoped
    asynchronous session tied to a specific service configuration and access
    context. It ensures that the session is properly committed at the end
    of successful operations or handled correctly in case of exceptions.

    Args:
        settings (ServiceSettings): Configuration settings for the service.
        access_context (AccessContext): Contextual information governing access.
        verify (bool): Flag to indicate whether session verification should
            be performed. Defaults to True.

    Yields:
        AsyncSession: An asynchronous session object to interact with the
        database.
    """
    async with access_scoped_session_ctx(
        session_factory=lambda: session_factory(settings),
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
    url = make_url(postgres_url.get_secret_value())
    if '+' in url.drivername:
        drivername = url.drivername.split('+', 1)[0]
        url = url.set(drivername=drivername)
    dsn = url.render_as_string(hide_password=False)
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
    """
    Dispose all database engines associated with a specific event loop.

    This asynchronous function disposes of all database engine instances that
    are tied to a particular event loop, freeing up resources. If no event loop
    is provided, it attempts to retrieve the current default event loop. If
    the retrieval of the event loop fails, the function exits gracefully.

    Args:
        loop (Loop | None): The specific event loop for which to dispose
            associated engines. If None, the current event loop is retrieved
            and used.

    Returns:
        None
    """
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
    """
    Tests the database connection using the provided settings.

    This function attempts to establish a database connection and logs the result.
    If the connection fails, it disposes of the database engines and raises a
    RuntimeError. It's intended to ensure the database service settings are
    correct and functional.

    Args:
        settings: The service settings required for establishing the database
            connection.

    Raises:
        RuntimeError: If the database connection could not be established.
    """
    try:
        await _test_db_connection_once(settings)
        logger.info('Database connection test successful')
    except Exception as exc:
        logger.exception('Database connection test failed')
        await dispose_engines()
        raise RuntimeError('Failed to connect to database') from exc
