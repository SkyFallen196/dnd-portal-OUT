"""Создаёт первого администратора.

Запуск (из папки backend, при активированном venv):
    python seed_admin.py

Данные администратора берутся из .env (или переменных окружения):
    ADMIN_EMAIL, ADMIN_PASSWORD  — ОБЯЗАТЕЛЬНЫ (дефолтов нет: пароль админа — критичный
                                   секрет, он не должен быть зашит в код);
    ADMIN_USERNAME               — необязателен, по умолчанию "admin".
Без ADMIN_EMAIL/ADMIN_PASSWORD скрипт падает с понятным сообщением.

Таблицы создаёт Alembic, поэтому перед этим скриптом нужно выполнить `alembic upgrade head`.
"""
import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.database import SessionLocal
from app.models import User
from app.security import hash_password


class AdminSeed(BaseSettings):
    """Читает данные админа из .env / окружения тем же способом, что и настройки приложения."""
    ADMIN_USERNAME: str = "admin"
    ADMIN_EMAIL: str
    ADMIN_PASSWORD: str

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


def main() -> None:
    try:
        cfg = AdminSeed()
    except ValidationError as exc:
        missing = [str(e["loc"][0]) for e in exc.errors() if e["type"] == "missing"]
        names = ", ".join(missing) if missing else "ADMIN_EMAIL, ADMIN_PASSWORD"
        sys.exit(
            f"\n[seed_admin] Не заданы обязательные данные админа: {names}.\n"
            f"Задай их в .env (в Docker — в корневом .env, нативно — в backend/.env).\n"
        )

    db = SessionLocal()
    try:
        existing = db.query(User).filter(
            (User.username == cfg.ADMIN_USERNAME) | (User.email == cfg.ADMIN_EMAIL)
        ).first()
        if existing:
            # Если пользователь уже есть — просто убедимся, что он админ и активен.
            existing.role = "admin"
            existing.is_active = True
            db.commit()
            print(f"Пользователь '{existing.username}' уже существует — сделан администратором.")
            return

        admin = User(
            username=cfg.ADMIN_USERNAME,
            email=cfg.ADMIN_EMAIL,
            password_hash=hash_password(cfg.ADMIN_PASSWORD),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Администратор создан:")
        print(f"  логин: {cfg.ADMIN_USERNAME}")
        print(f"  email: {cfg.ADMIN_EMAIL}")
        print("Смени пароль после первого входа: страница «Профиль» в портале.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
