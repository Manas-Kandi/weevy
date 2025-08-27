import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv

load_dotenv()
from .models import Base  # use single Base across app

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost/weev_db",
)

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    future=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

@asynccontextmanager
async def lifespan_healthcheck():
    """Simple connection check to validate DB connectivity on startup."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        yield True
    except Exception:  # pragma: no cover
        yield False

async def db_health() -> bool:
    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

async def init_db() -> None:
    """Placeholder for future startup logic (don't create tables here if using Alembic)."""
    # Using Alembic for migrations – nothing to do here.
    return None

async def close_db() -> None:
    await engine.dispose()

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session: Optional[AsyncSession] = None
    try:
        session = AsyncSessionLocal()
        yield session
    finally:
        if session is not None:
            await session.close()
