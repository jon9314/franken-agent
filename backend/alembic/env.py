import asyncio
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# This adds the root of the 'backend' directory to the Python path.
# It allows this script to import modules from your application (e.g., config, models).
sys.path.append(str(Path(__file__).resolve().parents[2]))

# Now we can import our app-specific components
from app.core.config import settings
from app.db.models import Base  # Your SQLAlchemy declarative base

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the target metadata for 'autogenerate' support.
# It tells Alembic what your SQLAlchemy models look like.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    This mode generates SQL scripts without connecting to a database.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """
    Helper function to run the migrations within a transaction.
    This is called by the online migration function.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    This mode connects to the database and applies the migrations.
    It's designed to work with an asyncio database driver.
    """
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,  # Use NullPool for single, short-lived connections
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine connection pool
    await connectable.dispose()


# Main entry point: decide whether to run in offline or online mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())