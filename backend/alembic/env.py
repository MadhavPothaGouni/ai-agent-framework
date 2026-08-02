
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Make sure every model is imported (and therefore registered on
# Base.metadata) before Alembic inspects it for autogenerate — mirrors
# the same import list app/main.py uses before create_all().
from app.db.session import Base, engine
from app.models import approval, budget, message, usage, user, workflow_run  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override whatever's in alembic.ini with the app's real, computed DB URL
# (same fallback-to-SQLite logic used everywhere else in the app).
config.set_main_option("sqlalchemy.url", str(engine.url))


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection — emits raw SQL."""
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
    """Run migrations against a live DB connection (the normal path)."""
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