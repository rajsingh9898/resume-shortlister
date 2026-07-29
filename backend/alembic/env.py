import sys
import os
from logging.config import fileConfig

from sqlalchemy import pool
from alembic import context

# Add backend project directory to python sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from database import engine, Base
except ImportError:
    from backend.database import engine, Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    try:
        from config import settings
    except ImportError:
        from backend.config import settings

    # Use DIRECT_URL for migrations if configured (important for Supabase transaction pools)
    url = getattr(settings, "DIRECT_URL", None) or os.getenv("DIRECT_URL") or str(engine.url)
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    from sqlalchemy import create_engine
    try:
        from config import settings
    except ImportError:
        from backend.config import settings

    migration_url = getattr(settings, "DIRECT_URL", None) or os.getenv("DIRECT_URL")
    if migration_url:
        connectable = create_engine(migration_url)
    else:
        connectable = engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
