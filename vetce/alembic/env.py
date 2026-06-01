"""Alembic environment script.

This is the entry point Alembic uses for every migration command.
It pulls the database URL from our project's settings (which reads .env),
and registers our SQLAlchemy models so autogenerate can detect changes.
"""
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Import our project's settings and model registry.
# Importing vetce.models triggers loading of all model classes,
# which registers them on Base.metadata — required for autogenerate.
from vetce.config import settings
from vetce.db import Base
import vetce.models  # noqa: F401 — imported for side effect of registering models

# Alembic Config object — gives access to values in alembic.ini.
config = context.config

# Override the sqlalchemy.url from alembic.ini with the one from our .env.
# This keeps credentials out of git.
config.set_main_option("sqlalchemy.url", settings.database_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is what autogenerate compares against the live database
# to detect schema changes.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode — emit SQL to a script without
    actually connecting to the database. Used for review/manual application."""
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
    """Run migrations in 'online' mode — connect to the database and
    apply changes directly. This is the normal path."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()