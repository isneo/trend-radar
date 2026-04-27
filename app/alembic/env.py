"""Alembic migration environment — sync driver (psycopg) for reliability."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import get_settings
from app.models import Base  # noqa: F401 — registers all models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Pull the sync URL from pydantic settings so it lives in .env.local — but
# only if no URL has been provided externally (e.g. by tests calling
# command.upgrade with a pre-set sqlalchemy.url).
if not config.get_main_option("sqlalchemy.url"):
    _settings = get_settings()
    config.set_main_option("sqlalchemy.url", _settings.database_url_sync)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
