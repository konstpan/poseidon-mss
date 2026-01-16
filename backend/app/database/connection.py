"""Async database connection and session management using SQLAlchemy 2.0."""

import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_async_database_url() -> str:
    """Convert standard database URL to async version."""
    url = settings.database_url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


# Create async SQLAlchemy engine with connection pooling
async_engine: AsyncEngine = create_async_engine(
    get_async_database_url(),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=300,  # Recycle connections after 5 minutes
    echo=settings.debug,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session dependency for FastAPI."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Check if database connection is healthy."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def init_db_engine() -> None:
    """Initialize database engine (call on startup)."""
    logger.info("Initializing database engine...")
    try:
        async with async_engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database engine initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database engine: {e}")
        raise


async def close_db_engine() -> None:
    """Close database engine (call on shutdown)."""
    logger.info("Closing database engine...")
    await async_engine.dispose()
    logger.info("Database engine closed")


from contextlib import asynccontextmanager


@asynccontextmanager
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Get async database session as context manager (for non-FastAPI use).

    Usage:
        async with get_async_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# Aliases for backward compatibility
engine = async_engine
get_db = get_async_db
