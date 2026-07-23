"""Фишки на карте: список, создание, изменение, удаление, аватар.

Фишка (Token) — это кружок на карте комнаты. Лист персонажа со всеми характеристиками —
это другая сущность, HeroSheet («свиток»), она живёт в routers/heroes.py.
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..combat import broadcast_combat, drop_from_combat
from ..database import get_db
from ..models import Token, User
from ..room_access import ensure_dm, ensure_member, get_room_or_404, is_room_dm
from ..schemas import TokenCreateIn, TokenOut, TokenUpdateIn
from ..security import admin_edit_mode, require_active_subscription
from ..storage import delete_upload_if_unused
from ..ws_manager import manager

router = APIRouter(prefix="/rooms/{room_id}/tokens", tags=["tokens"])

# Аватары храним в той же папке, что и карты (её раздаёт StaticFiles на /uploads).
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5 МБ


async def broadcast_token(
    room_id: int, tk: Token, event: str, was_hidden: bool | None = None
) -> None:
    """Разослать изменение фишки с учётом скрытности.

    Скрытая фишка не должна доходить до игроков вообще — ни в одном событии.
    Момент, когда её прячут или показывают, для игроков выглядит как исчезновение
    или появление фишки.
    """
    payload = {"type": event, "token": token_payload(tk)}

    if was_hidden is not None and was_hidden != tk.hidden:
        if tk.hidden:
            # Спрятали: у игроков фишка должна пропасть с карты.
            await manager.broadcast_split(room_id, payload, {"type": "token_removed", "token_id": tk.id})
        else:
            # Показали: у игроков она появляется как новая.
            await manager.broadcast_split(room_id, payload, {"type": "token_added", "token": token_payload(tk)})
        return

    await manager.broadcast(room_id, payload, dm_only=tk.hidden)


@router.get("", response_model=list[TokenOut])
def list_tokens(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> list[Token]:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    query = select(Token).where(Token.room_id == room_id)
    if not is_room_dm(room, user, admin_edit):
        query = query.where(Token.hidden.is_(False))
    # Порядок отрисовки: снизу вверх по z. При равном z — по id, чтобы у всех
    # за столом фишки лежали одинаково, а не как повезёт с порядком в выдаче.
    return list(db.scalars(query.order_by(Token.z, Token.id)))


@router.post("", response_model=TokenOut)
async def create_token(
    room_id: int,
    data: TokenCreateIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Token:
    """Мастер ставит на карту фишку персонажа или NPC. Может назначить владельца (игрока)."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    tk = Token(
        room_id=room_id,
        owner_user_id=data.owner_user_id,
        name=data.name,
        color=data.color,
        x=data.x,
        y=data.y,
        # Текущее HP не может быть больше максимума — проверяем здесь, а не только в интерфейсе.
        hp=min(data.hp, data.max_hp),
        max_hp=data.max_hp,
        is_npc=data.is_npc,
        hidden=data.hidden,
    )
    db.add(tk)
    db.commit()
    db.refresh(tk)
    await broadcast_token(room_id, tk, "token_added")
    return tk


@router.patch("/{token_id}", response_model=TokenOut)
async def update_token(
    room_id: int,
    token_id: int,
    data: TokenUpdateIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Token:
    """Изменить фишку. Двигать может владелец или мастер; остальные поля — только мастер."""
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    tk = db.get(Token, token_id)
    if tk is None or tk.room_id != room_id:
        raise HTTPException(status_code=404, detail="Фишка не найдена")

    is_dm = is_room_dm(room, user, admin_edit)
    is_owner = tk.owner_user_id == user.id

    was_hidden = tk.hidden
    fields = data.model_dump(exclude_unset=True)
    changed = set(fields.keys())
    only_moving = changed <= {"x", "y"}
    # Владельцу, кроме перемещения, разрешён и z: поднять свою фишку из-под чужой —
    # часть обычной игры, а не правка характеристик персонажа.
    owner_allowed = changed <= {"x", "y", "z"}

    if not is_dm and not (is_owner and owner_allowed):
        raise HTTPException(status_code=403, detail="Нет прав менять эту фишку")

    for key, value in fields.items():
        setattr(tk, key, value)
    # Страховка на сервере: сколько бы ни прислал клиент, hp остаётся в пределах 0..max_hp.
    # Нужна и когда снижают max_hp у раненого персонажа — тогда текущее HP подтягивается вниз.
    tk.hp = max(0, min(tk.hp, tk.max_hp))
    db.commit()
    db.refresh(tk)

    event = "token_moved" if only_moving else "token_updated"
    await broadcast_token(room_id, tk, event, was_hidden=was_hidden)
    return tk


@router.delete("/{token_id}", status_code=204)
async def delete_token(
    room_id: int,
    token_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> None:
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    tk = db.get(Token, token_id)
    if tk is None or tk.room_id != room_id:
        raise HTTPException(status_code=404, detail="Фишка не найдена")
    avatar = tk.avatar_url
    # Если убирают фишку, чей сейчас ход, — сначала передаём ход дальше, иначе бой замрёт.
    combat_changed = drop_from_combat(db, room, [tk.id])
    db.delete(tk)
    db.commit()
    # Аватар удаляем, только если это не портрет свитка, из которого фишку выставили.
    delete_upload_if_unused(db, avatar)
    await manager.broadcast(room_id, {"type": "token_removed", "token_id": token_id})
    if combat_changed:
        await broadcast_combat(db, room)


@router.post("/{token_id}/avatar", response_model=TokenOut)
async def upload_avatar(
    room_id: int,
    token_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Token:
    """Загрузить картинку фишки. Может мастер комнаты или владелец фишки."""
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    tk = db.get(Token, token_id)
    if tk is None or tk.room_id != room_id:
        raise HTTPException(status_code=404, detail="Фишка не найдена")

    is_dm = is_room_dm(room, user, admin_edit)
    if not is_dm and tk.owner_user_id != user.id:
        raise HTTPException(status_code=403, detail="Нет прав менять эту фишку")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только изображения (png/jpeg/webp/gif)")
    content = await file.read()
    if len(content) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 5 МБ)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    stored_name = f"avatar_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    old_avatar = tk.avatar_url
    tk.avatar_url = f"/uploads/{stored_name}"
    db.commit()
    db.refresh(tk)
    delete_upload_if_unused(db, old_avatar)
    await broadcast_token(room_id, tk, "token_updated")
    return tk


def token_payload(tk: Token) -> dict:
    """Как фишка выглядит в событиях WebSocket (совпадает с TokenOut)."""
    return {
        "id": tk.id,
        "room_id": tk.room_id,
        "owner_user_id": tk.owner_user_id,
        "hero_sheet_id": tk.hero_sheet_id,
        "name": tk.name,
        "color": tk.color,
        "avatar_url": tk.avatar_url,
        "x": tk.x,
        "y": tk.y,
        "hp": tk.hp,
        "max_hp": tk.max_hp,
        "is_npc": tk.is_npc,
        "size": tk.size,
        "effects": tk.effects or [],
        "initiative": tk.initiative,
        "hidden": tk.hidden,
        "z": tk.z,
    }
