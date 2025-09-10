from __future__ import annotations

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool, MetaData, Table, Column
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.dialects.postgresql import UUID as PGUUID

from alembic import context

# Ensure `app/` is importable when running alembic from anywhere
THIS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = THIS_DIR.parent  # services/inventory
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import settings and Base
from app.settings import settings  # noqa: E402
from app.db import Base  # noqa: E402

# Import models so Alembic can autogenerate tables
import app.models  # noqa: F401,E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# metadata for autogenerate
target_metadata = Base.metadata

# Ensure a dummy 'users' table exists in metadata for FK resolution during autogenerate,
# but exclude it from generation via include_object below.
if "users" not in Base.metadata.tables:
    Table(
        "users",
        Base.metadata,
        Column("id", PGUUID(as_uuid=True)),
        extend_existing=True,
    )

# Only allow real inventory tables (exclude the dummy 'users')
_ALLOWED_TABLES = {name for name in Base.metadata.tables.keys() if name != "users"}


def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in _ALLOWED_TABLES
    if type_ == "index":
        try:
            tbl = object.table.name  # type: ignore[attr-defined]
        except Exception:
            tbl = None
        return tbl in _ALLOWED_TABLES
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configure the context with just a URL and not an Engine.
    """
    url = settings.POSTGRES_DSN
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        version_table="alembic_version_inventory",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Configure with our metadata only; dummy 'users' is present for FK resolution
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        version_table="alembic_version_inventory",
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async Engine and associate a connection with the context."""
    connectable = async_engine_from_config(
        {
            **(config.get_section(config.config_ini_section, {}) or {}),
            "sqlalchemy.url": settings.POSTGRES_DSN,
        },
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
