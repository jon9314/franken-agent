import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# This line allows the alembic env.py to see your app models
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import your app's settings and Base model
from app.core.config import settings
from app.db.database import Base
from app.db import models as app_models # This ensures all models are loaded for 'autogenerate'

target_metadata = Base.metadata

# Override sqlalchemy.url from alembic.ini with the one from your app's config
config.set_main_option('sqlalchemy.url', str(settings.DATABASE_URL))


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
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
    """
    Run migrations in 'online' mode.
    This version is SYNCHRONOUS and matches our SQLite driver.
    """
    # --- THIS IS THE FINAL CORRECTED PART ---
    # We get the section named 'alembic' directly from the config object.
    alembic_config_section = config.get_section(config.config_ini_section)
    
    # And we update it with the database URL from our main application settings
    alembic_config_section['sqlalchemy.url'] = str(settings.DATABASE_URL)

    connectable = engine_from_config(
        alembic_config_section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Associate a connection with the context
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        # Run the migrations within a transaction
        with context.begin_transaction():
            context.run_migrations()


# Main entry point: decide whether to run in offline or online mode.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()