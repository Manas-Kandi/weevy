import asyncio
import os
import uuid
import pytest
from typing import AsyncGenerator

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from httpx import AsyncClient

# Ensure app import finds Backend as module root when running from repo root
import sys
from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from main import app  # noqa: E402
from database import models  # noqa: E402
from database.connection import get_session  # noqa: E402


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine():
    test_url = os.getenv("DATABASE_TEST_URL") or "postgresql+asyncpg://user:password@localhost/weev_test_db"
    engine = create_async_engine(test_url, echo=False, future=True)

    # Create schema
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
    try:
        yield engine
    finally:
        # Drop schema
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.drop_all)
        await engine.dispose()


@pytest.fixture()
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture()
async def client(db_session: AsyncSession):
    # Override dependency
    async def _get_test_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _get_test_session

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
