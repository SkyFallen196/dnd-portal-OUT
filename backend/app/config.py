"""Настройки приложения.

Секреты (адрес БД с паролем и ключ подписи токенов) НЕ имеют значений по умолчанию:
приложение не должно запускаться с предсказуемым ключом, зашитым в код. Их задаёт файл
`.env` (см. `.env.example`) или переменные окружения. Если секрета нет — падаем сразу,
с понятным сообщением, а не работаем «дырявыми».
"""
import sys

from pydantic import ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # --- Секреты: обязательны, дефолтов нет ---
    # Строка подключения к БД (внутри неё — пароль): postgresql+psycopg2://user:pass@host:port/db
    DATABASE_URL: str
    # Ключ подписи JWT: длинная случайная строка. Сгенерировать:
    #   python -c "import secrets; print(secrets.token_urlsafe(48))"
    JWT_SECRET: str

    # --- Не секреты: разумные значения по умолчанию ---
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7 дней
    FRONTEND_ORIGIN: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


try:
    # Один общий объект настроек на всё приложение.
    settings = Settings()
except ValidationError as exc:
    missing = [str(e["loc"][0]) for e in exc.errors() if e["type"] == "missing"]
    names = ", ".join(missing) if missing else "обязательные настройки"
    sys.exit(
        f"\n[config] Не заданы обязательные секреты: {names}.\n"
        f"Скопируй backend/.env.example в backend/.env и заполни значения\n"
        f"(в Docker они приходят из корневого .env — см. README).\n"
    )
