"""Заметки и раздаточные материалы комнаты.

Мастер готовит их заранее (описание таверны, текст найденного письма, портрет NPC)
и открывает партии по ходу игры. Пока материал не «опубликован», его не видит никто,
кроме мастера — и это проверяется на сервере, а не в интерфейсе.
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Handout, User
from ..room_access import ensure_dm, ensure_member, get_room_or_404, is_room_dm
from ..schemas import HandoutIn, HandoutOut, HandoutUpdateIn
from ..security import admin_edit_mode, require_active_subscription
from ..storage import delete_upload_if_unused
from ..ws_manager import manager

router = APIRouter(prefix="/rooms/{room_id}/handouts", tags=["handouts"])

# Картинки материалов лежат там же, где карты и аватары — их раздаёт StaticFiles на /uploads.
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 МБ


def handout_payload(h: Handout) -> dict:
    """Как материал выглядит в событиях WebSocket (совпадает с HandoutOut)."""
    return {
        "id": h.id,
        "room_id": h.room_id,
        "title": h.title,
        "body": h.body,
        "image_url": h.image_url,
        "is_public": h.is_public,
        "created_at": h.created_at.isoformat(),
    }


async def broadcast_handout(room_id: int, h: Handout, was_public: bool | None = None) -> None:
    """Разослать изменение материала с учётом публичности.

    Логика та же, что у скрытых фишек: непубличный материал не уходит игрокам вообще.
    Момент публикации для них выглядит как появление материала, снятие с публикации —
    как исчезновение.
    """
    payload = {"type": "handout_updated", "handout": handout_payload(h)}

    if was_public is not None and was_public != h.is_public:
        player_message = payload if h.is_public else {"type": "handout_removed", "handout_id": h.id}
        await manager.broadcast_split(room_id, payload, player_message)
        return

    await manager.broadcast(room_id, payload, dm_only=not h.is_public)


def _get_handout(db: Session, room_id: int, handout_id: int) -> Handout:
    h = db.get(Handout, handout_id)
    if h is None or h.room_id != room_id:
        raise HTTPException(status_code=404, detail="Материал не найден")
    return h


@router.get("", response_model=list[HandoutOut])
def list_handouts(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> list[Handout]:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    query = select(Handout).where(Handout.room_id == room_id)
    if not is_room_dm(room, user, admin_edit):
        query = query.where(Handout.is_public.is_(True))
    return list(db.scalars(query.order_by(Handout.created_at)))


@router.post("", response_model=HandoutOut)
async def create_handout(
    room_id: int,
    data: HandoutIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Handout:
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    h = Handout(
        room_id=room_id,
        title=data.title,
        body=data.body,
        is_public=data.is_public,
        created_by=user.id,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    await broadcast_handout(room_id, h)
    return h


@router.patch("/{handout_id}", response_model=HandoutOut)
async def update_handout(
    room_id: int,
    handout_id: int,
    data: HandoutUpdateIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Handout:
    """Изменить материал или показать/спрятать его от партии."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    h = _get_handout(db, room_id, handout_id)

    was_public = h.is_public
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(h, key, value)
    db.commit()
    db.refresh(h)
    await broadcast_handout(room_id, h, was_public=was_public)
    return h


@router.delete("/{handout_id}", status_code=204)
async def delete_handout(
    room_id: int,
    handout_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> None:
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    h = _get_handout(db, room_id, handout_id)

    image = h.image_url
    was_public = h.is_public
    db.delete(h)
    db.commit()
    # Картинку удаляем только если на неё больше никто не ссылается (её могли
    # переиспользовать как портрет свитка или аватар фишки).
    delete_upload_if_unused(db, image)

    payload = {"type": "handout_removed", "handout_id": handout_id}
    # Непубличный материал игроки и не видели — им сообщать не о чем.
    await manager.broadcast(room_id, payload, dm_only=not was_public)


@router.post("/{handout_id}/image", response_model=HandoutOut)
async def upload_handout_image(
    room_id: int,
    handout_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Handout:
    """Прикрепить картинку: портрет NPC, карта города, изображение находки."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    h = _get_handout(db, room_id, handout_id)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только изображения (png/jpeg/webp/gif)")
    content = await file.read()
    if len(content) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 10 МБ)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    stored_name = f"handout_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    old_image = h.image_url
    h.image_url = f"/uploads/{stored_name}"
    db.commit()
    db.refresh(h)
    delete_upload_if_unused(db, old_image)
    await broadcast_handout(room_id, h)
    return h
