"""Настройка окружения Alembic.

Адрес базы и описание таблиц берём прямо из приложения, чтобы они не разъезжались:
- DATABASE_URL — из app.config.settings (то есть из .env / переменных окружения);
- список таблиц — из app.models через Base.metadata.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.config import settings
from app.database import Base
from app import models  # noqa: F401  — импорт нужен, чтобы модели зарегистрировались в Base

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# По этой схеме Alembic сравнивает модели с реальной БД (autogenerate).
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Режим без подключения к БД: печатает SQL вместо выполнения."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Обычный режим: подключаемся к БД и применяем миграции."""
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
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
