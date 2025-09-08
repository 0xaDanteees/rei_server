from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from .settings import settings

Base = declarative_base()

from typing import Optional
_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.POSTGRES_DSN,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=False,
            pool_timeout=30,
            pool_recycle=1800,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _SessionLocal


async def init_db() -> None:
    # Connectivity check and create tables for MVP
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        try:
            # Import models lazily to avoid cycles
            from . import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)
        except Exception:
            # If DDL fails (permissions), at least continue running
            pass


async def close_db() -> None:
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None


# FastAPI dependency
async def get_db() -> AsyncSession:
    Session = get_session_factory()
    async with Session() as session:
        yield session
