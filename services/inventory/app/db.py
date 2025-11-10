from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text, Table
from fastapi import HTTPException, status
from .settings import settings
import ssl
import certifi

Base = declarative_base()

from typing import Optional
_engine: Optional[AsyncEngine] = None
_SessionLocal: Optional[sessionmaker] = None


def is_db_enabled() -> bool:
    return bool(settings.POSTGRES_DSN)

ssl_ctx = ssl.create_default_context(cafile=certifi.where())
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        if not is_db_enabled():
            raise RuntimeError("Database is disabled (no POSTGRES_DSN).")
        
        # For Supabase pgBouncer with psycopg: simpler config
        _engine = create_async_engine(
            settings.POSTGRES_DSN,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            echo=False,
            connect_args={"sslmode": "require"},
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _SessionLocal
    if _SessionLocal is None:
        if not is_db_enabled():
            raise RuntimeError("Database is disabled (no POSTGRES_DSN).")
        _SessionLocal = sessionmaker(bind=get_engine(), class_=AsyncSession, expire_on_commit=False)
    return _SessionLocal


async def init_db() -> None:
    # Skip entirely if DB is disabled (stateless mode for Vercel)
    if not is_db_enabled():
        return
    # Connectivity check and create tables for MVP
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.execute(text("SELECT 1"))
        try:
            # Reflect external 'users' table into our metadata to satisfy FK references
            def _reflect_users(sync_conn):
                try:
                    Table("users", Base.metadata, autoload_with=sync_conn)
                except Exception:
                    # If reflection fails (table missing), continue; FK ops will fail accordingly
                    pass

            await conn.run_sync(_reflect_users)

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
    if not is_db_enabled():
        # Return a consistent error envelope upstream via exception handlers
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database unavailable in this environment")
    Session = get_session_factory()
    async with Session() as session:
        yield session
