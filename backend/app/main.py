"""Точка входа приложения FastAPI."""
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .routers import admin, auth, codes, combat, dice, handouts, heroes, rooms, tokens, ws

# Таблицы приложение больше НЕ создаёт само: схемой заведует Alembic.
# Перед запуском сервера нужно выполнить (из папки backend):
#     alembic upgrade head
# В Docker это делается автоматически — см. команду сервиса backend в docker-compose.yml.

app = FastAPI(title="D&D Portal API", version="1.0.0")

# Разрешаем фронтенду обращаться к API (CORS).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Папка для загруженных карт и её раздача по адресу /uploads/...
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Подключаем все группы эндпоинтов.
app.include_router(auth.router)
app.include_router(codes.router)
app.include_router(rooms.router)
app.include_router(tokens.router)
app.include_router(dice.router)
app.include_router(combat.router)
app.include_router(handouts.router)
app.include_router(heroes.router)
app.include_router(admin.router)
app.include_router(ws.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    # Возвращаем 500 как обычный ответ, чтобы к нему добавились CORS-заголовки
    # и фронтенд показал текст ошибки, а не абстрактный "network error".
    return JSONResponse(status_code=500, content={"detail": f"Ошибка сервера: {exc}"})


@app.get("/")
def health() -> dict:
    return {"status": "ok", "service": "dnd-portal"}
