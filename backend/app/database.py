"""Подключение к базе данных через SQLAlchemy (синхронный режим)."""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

# "Движок" — объект, который умеет открывать соединения с PostgreSQL.
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# Фабрика сессий. Сессия — это "рабочая область" для одного запроса к БД.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей (таблиц)."""


def get_db() -> Generator[Session, None, None]:
    """FastAPI-зависимость: выдаёт сессию и гарантированно закрывает её после запроса."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
