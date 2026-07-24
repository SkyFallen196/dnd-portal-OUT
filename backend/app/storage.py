"""Работа с загруженными файлами (папка uploads).

Один и тот же файл может быть привязан к нескольким записям сразу: когда свиток героя
выставляют на карту, портрет свитка становится ещё и аватаром фишки — путь у них общий.
Поэтому файл нельзя удалять «за компанию» с записью: сначала проверяем, не ссылается ли
на него кто-то ещё, и только потом стираем с диска.
"""
import os

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Handout, HeroSheet, MapImage, Token

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
URL_PREFIX = "/uploads/"


def is_referenced(db: Session, url: str) -> bool:
    """Ссылается ли на файл хоть одна запись в базе."""
    checks = (
        select(Token.id).where(Token.avatar_url == url),
        select(HeroSheet.id).where(HeroSheet.portrait_url == url),
        select(MapImage.id).where(MapImage.file_path == url),
        select(Handout.id).where(Handout.image_url == url),
    )
    return any(db.scalar(q.limit(1)) is not None for q in checks)


def delete_upload_if_unused(db: Session, url: str | None) -> bool:
    """Удалить файл с диска, если на него больше никто не ссылается.

    Вызывать ПОСЛЕ commit, иначе в базе ещё видна удаляемая запись и файл уцелеет.
    Возвращает True, если файл действительно удалён.
    """
    if not url or not url.startswith(URL_PREFIX):
        return False
    # Защита от попыток вылезти из папки uploads через путь вида /uploads/../../secret
    name = os.path.basename(url)
    if not name or name in (".", ".."):
        return False
    if is_referenced(db, url):
        return False

    path = os.path.join(UPLOAD_DIR, name)
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False
    except OSError:
        # Файл занят или нет прав — не роняем из-за этого запрос пользователя.
        return False


def delete_uploads_if_unused(db: Session, urls: list[str | None]) -> int:
    """То же самое для списка файлов. Возвращает, сколько удалено."""
    return sum(1 for url in urls if delete_upload_if_unused(db, url))


def room_file_urls(db: Session, room_id: int) -> list[str | None]:
    """Все файлы, привязанные к комнате: карты, картинки фишек и раздаточных материалов.

    Собирать НУЖНО до удаления комнаты — после каскадного удаления записей уже не найти.
    """
    maps = list(db.scalars(select(MapImage.file_path).where(MapImage.room_id == room_id)))
    avatars = list(db.scalars(select(Token.avatar_url).where(Token.room_id == room_id)))
    images = list(db.scalars(select(Handout.image_url).where(Handout.room_id == room_id)))
    return maps + avatars + images
