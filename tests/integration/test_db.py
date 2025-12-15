from uuid import uuid4

import pytest
from sqlalchemy import text
from tenauth.schemas import AccessContext

from nexor.infrastructure import db

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_session_factory_can_execute_queries(db_settings):
    async with db.session_factory(db_settings) as session:
        result = await session.execute(text('SELECT 1'))  # simple identity check
        assert result.scalar_one() == 1


@pytest.mark.asyncio
async def test_scoped_session_binds_tenant_context(db_settings):
    tenant_id = uuid4()
    user_id = uuid4()
    access_ctx = AccessContext(tenant_id=tenant_id, user_id=user_id)

    async with db.scoped_session(settings=db_settings, access_context=access_ctx) as session:
        tenant_result = await session.execute(text("SELECT current_setting('app.tenant_id')"))
        user_result = await session.execute(text("SELECT current_setting('app.user_id')"))

        assert tenant_result.scalar_one() == str(tenant_id)
        assert user_result.scalar_one() == str(user_id)


@pytest.mark.asyncio
async def test_pg_connection_applies_tenant_settings(postgres_url):
    tenant_id = uuid4()
    async with db.pg_connection(postgres_url, tenant_id) as conn:
        current_tenant = await conn.fetchval("SELECT current_setting('app.tenant_id')")
        assert current_tenant == str(tenant_id)


@pytest.mark.asyncio
async def test_test_db_connection_is_successful(db_settings):
    await db.test_db_connection(db_settings)
