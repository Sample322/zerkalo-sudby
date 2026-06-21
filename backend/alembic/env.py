"""Alembic async migration environment (RESEARCH Pattern 1).

The migration runner is synchronous; for an async engine we wrap it with
``connection.run_sync`` inside ``asyncio.run``. The DB URL is injected from app
settings (not ``alembic.ini``) and ``Base.metadata`` is the autogenerate target.
Plan 02 generates the first revision (all 16 tables) against this scaffold.

The DSN is normalised through ``app.core.db_url`` so a libpq ``?sslmode=...`` param on a
managed-Postgres URL becomes an asyncpg ``connect_args={"ssl": ...}`` (asyncpg rejects
``sslmode``) — the migration engine and the app engine treat SSL identically.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context
from app.core.config import settings
from app.core.db_url import async_url_and_connect_args
from app.models.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Normalise the env-driven DSN (strip libpq sslmode → asyncpg connect_args).
_clean_url, _connect_args = async_url_and_connect_args(settings.DATABASE_URL)

# Inject the cleaned DSN (no sslmode) so offline mode + any config readers see a valid asyncpg URL.
config.set_main_option("sqlalchemy.url", _clean_url)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(
        _clean_url,
        poolclass=pool.NullPool,
        connect_args=_connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DB connection (``alembic upgrade --sql``)."""
    context.configure(
        url=_clean_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
