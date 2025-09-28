from __future__ import annotations

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings


class Base(DeclarativeBase):
    pass


_settings = get_settings()
_engine: AsyncEngine = create_async_engine(
    _settings.database_url,
    echo=False,
    future=True,
)
SessionLocal = async_sessionmaker(
    bind=_engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def session_manager() -> AsyncSession:
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def init_database() -> None:
    """Create tables if they are missing. Real deployments should use migrations."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
