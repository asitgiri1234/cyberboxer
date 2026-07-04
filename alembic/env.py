"""
Alembic migration environment.

This wires Alembic into the existing application configuration so there is a
single source of truth:

* the database URL comes from `app.config.settings` (which reads the `.env`
  file), NOT from `alembic.ini`, and
* the target schema is `app.database.Base.metadata`, populated by importing the
  ORM models.

Both offline (SQL script) and online (live connection) modes are supported.
"""

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Application configuration and ORM metadata.
from app.config import settings
from app.database import Base

# Importing the models package registers every table on `Base.metadata`, which
# is what Alembic autogenerate compares against.
import app.models  # noqa: F401  (side effect: registers models)

# Alembic Config object (provides access to values in alembic.ini).
config = context.config

# Inject the database URL from the app settings so it is not duplicated in
# alembic.ini and secrets never live in version control.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure Python logging from alembic.ini if present.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic diffs against for autogeneration.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL, no DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,             # detect column type changes
        compare_server_default=True,   # detect server-default changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (against a live database connection)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
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
