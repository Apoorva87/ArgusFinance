"""Alembic environment for ArgusFinance operational metadata."""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from argusfinance.config import Settings
from argusfinance.storage.database import ensure_sqlite_file_parent
from argusfinance.storage.models import Base

config = context.config

# Programmatic callers that inject a URL set this attribute so tests and tools
# remain isolated from the caller's ambient environment and .env file.
if not config.attributes.get("argus_database_url_explicit", False):
    config.set_main_option("sqlalchemy.url", Settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations without an active database connection."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against the configured local database."""
    ensure_sqlite_file_parent(config.get_main_option("sqlalchemy.url"))
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
