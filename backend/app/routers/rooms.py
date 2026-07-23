"""Комнаты (игровые столы), участники и загрузка карты."""
import os
import secrets
import string
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..combat import broadcast_combat, drop_from_combat
from ..database import get_db
from ..models import MapImage, Room, RoomMember, Token, User
from ..room_access import ensure_dm, ensure_member, get_room_or_404
from ..schemas import (
    MapOut,
    MemberOut,
    RoomCreateIn,
    RoomDetailOut,
    RoomJoinIn,
    RoomOut,
    RoomUpdateIn,
)
from ..security import admin_edit_mode, require_active_subscription
from ..storage import delete_upload_if_unused, delete_uploads_if_unused, room_file_urls
from ..ws_manager import manager

router = APIRouter(prefix="/rooms", tags=["rooms"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_MAP_BYTES = 15 * 1024 * 1024  # 15 МБ


def _invite_code() -> str:
    return "".join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6))


def _room_detail(db: Session, room: Room) -> RoomDetailOut:
    members = [
        MemberOut(user_id=m.user.id, username=m.user.username, role=m.user.role)
        for m in room.members
    ]
    active_map = db.get(MapImage, room.active_map_id) if room.active_map_id else None
    return RoomDetailOut(
        id=room.id,
        name=room.name,
        dm_id=room.dm_id,
        invite_code=room.invite_code,
        active_map_id=room.active_map_id,
        grid_size=room.grid_size,
        created_at=room.created_at,
        members=members,
        active_map=MapOut.model_validate(active_map) if active_map else None,
    )


@router.get("", response_model=list[RoomOut])
def my_rooms(
    user: User = Depends(require_active_subscription), db: Session = Depends(get_db)
) -> list[Room]:
    """Комнаты, где пользователь — мастер или участник."""
    as_dm = select(Room).where(Room.dm_id == user.id)
    as_member = (
        select(Room).join(RoomMember, RoomMember.room_id == Room.id).where(RoomMember.user_id == user.id)
    )
    rooms = {r.id: r for r in db.scalars(as_dm)}
    rooms.update({r.id: r for r in db.scalars(as_member)})
    return list(rooms.values())


@router.post("", response_model=RoomDetailOut)
def create_room(
    data: RoomCreateIn,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> RoomDetailOut:
    """Создать комнату. Нужна игровая роль мастера (её выдаёт админ).

    Быть админом недостаточно: админство — это управление порталом, а не право водить игру.
    """
    if not user.is_dm:
        raise HTTPException(
            status_code=403,
            detail="Создавать комнаты может только мастер подземелий (DM). Роль DM выдаёт администратор.",
        )

    code = _invite_code()
    while db.scalar(select(Room).where(Room.invite_code == code)):
        code = _invite_code()

    room = Room(name=data.name, dm_id=user.id, invite_code=code)
    db.add(room)
    db.flush()
    db.add(RoomMember(room_id=room.id, user_id=user.id))
    db.commit()
    db.refresh(room)
    return _room_detail(db, room)


@router.post("/join", response_model=RoomDetailOut)
def join_room(
    data: RoomJoinIn,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> RoomDetailOut:
    room = db.scalar(select(Room).where(Room.invite_code == data.invite_code.strip().upper()))
    if room is None:
        raise HTTPException(status_code=404, detail="Комната с таким кодом не найдена")
    already = db.scalar(
        select(RoomMember).where(RoomMember.room_id == room.id, RoomMember.user_id == user.id)
    )
    if not already:
        db.add(RoomMember(room_id=room.id, user_id=user.id))
        db.commit()
    db.refresh(room)
    return _room_detail(db, room)


@router.get("/{room_id}", response_model=RoomDetailOut)
def get_room(
    room_id: int,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> RoomDetailOut:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    return _room_detail(db, room)


@router.patch("/{room_id}", response_model=RoomDetailOut)
async def update_room(
    room_id: int,
    data: RoomUpdateIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> RoomDetailOut:
    """Настройки комнаты (название, сетка). Меняет мастер.

    Сетка живёт у комнаты, а не в браузере: масштаб подбирают под конкретную карту,
    и линейка должна мерить одинаково у всех за столом.
    """
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    fields = data.model_dump(exclude_unset=True)
    for key, value in fields.items():
        setattr(room, key, value)
    db.commit()
    db.refresh(room)

    if "grid_size" in fields:
        await manager.broadcast(room_id, {"type": "room_updated", "grid_size": room.grid_size})
    return _room_detail(db, room)


@router.delete("/{room_id}", status_code=204)
async def delete_room(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> None:
    """Удалить комнату целиком. Может мастер комнаты или админ.

    БД каскадно удалит участников, персонажей, карты и броски этой комнаты.
    """
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    # Пути к файлам собираем ДО удаления — после каскада записей уже не будет.
    files = room_file_urls(db, room_id)
    db.delete(room)
    db.commit()
    delete_uploads_if_unused(db, files)
    # Сообщаем всем, кто был в комнате, чтобы их выкинуло на список комнат.
    await manager.broadcast(room_id, {"type": "room_deleted", "room_id": room_id})


async def _drop_member(db: Session, room: Room, user_id: int) -> None:
    """Убрать участника из комнаты вместе с его фишками.

    Общая часть для двух случаев: мастер исключил игрока и игрок вышел сам. Фишки уносим
    потому, что человек больше не в игре: двигать их он всё равно не сможет (проверка
    участия), а на карте они висели бы мёртвым грузом, и разбираться пришлось бы мастеру.
    """
    member = db.scalar(
        select(RoomMember).where(RoomMember.room_id == room.id, RoomMember.user_id == user_id)
    )
    if member is None:
        return

    tokens = list(
        db.scalars(select(Token).where(Token.room_id == room.id, Token.owner_user_id == user_id))
    )
    removed_ids = [tk.id for tk in tokens]
    avatars = [tk.avatar_url for tk in tokens]

    # Вышедший мог быть в бою — и даже ходить прямо сейчас.
    combat_changed = drop_from_combat(db, room, removed_ids)
    for tk in tokens:
        db.delete(tk)
    db.delete(member)
    db.commit()

    for url in avatars:
        delete_upload_if_unused(db, url)
    for token_id in removed_ids:
        await manager.broadcast(room.id, {"type": "token_removed", "token_id": token_id})
    if combat_changed:
        await broadcast_combat(db, room)


@router.delete("/{room_id}/members/{user_id}", status_code=204)
async def remove_member(
    room_id: int,
    user_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> None:
    """Мастер исключает игрока из комнаты."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    if user_id == room.dm_id:
        raise HTTPException(status_code=400, detail="Нельзя удалить мастера из его комнаты")
    await _drop_member(db, room, user_id)


@router.post("/{room_id}/leave", status_code=204)
async def leave_room(
    room_id: int,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> None:
    """Игрок сам выходит из комнаты. Вернуться можно по коду приглашения.

    Мастер выйти не может: комната без мастера никому не нужна — её удаляют целиком
    (DELETE /rooms/{id}).
    """
    room = get_room_or_404(db, room_id)
    if room.dm_id == user.id:
        raise HTTPException(
            status_code=400,
            detail="Мастер не может выйти из своей комнаты — её можно только удалить",
        )
    member = db.scalar(
        select(RoomMember).where(RoomMember.room_id == room_id, RoomMember.user_id == user.id)
    )
    if member is None:
        raise HTTPException(status_code=400, detail="Вы не состоите в этой комнате")
    await _drop_member(db, room, user.id)


def _map_payload(m: MapImage | None) -> dict | None:
    """Как карта выглядит в событии WebSocket (совпадает с MapOut)."""
    if m is None:
        return None
    return {
        "id": m.id,
        "filename": m.filename,
        "file_path": m.file_path,
        "width": m.width,
        "height": m.height,
    }


@router.get("/{room_id}/maps", response_model=list[MapOut])
def list_maps(
    room_id: int,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> list[MapImage]:
    """Все карты комнаты. Мастер переключается между ними, не загружая заново."""
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    return list(
        db.scalars(
            select(MapImage).where(MapImage.room_id == room_id).order_by(MapImage.created_at)
        )
    )


@router.post("/{room_id}/maps/{map_id}/activate", response_model=MapOut)
async def activate_map(
    room_id: int,
    map_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> MapImage:
    """Сделать одну из загруженных карт активной (например, вернуться из подземелья в таверну)."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    map_row = db.get(MapImage, map_id)
    if map_row is None or map_row.room_id != room_id:
        raise HTTPException(status_code=404, detail="Карта не найдена")

    room.active_map_id = map_row.id
    db.commit()
    db.refresh(map_row)
    await manager.broadcast(room_id, {"type": "map_changed", "map": _map_payload(map_row)})
    return map_row


@router.delete("/{room_id}/maps/{map_id}", status_code=204)
async def delete_map(
    room_id: int,
    map_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> None:
    """Удалить карту вместе с её файлом."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    map_row = db.get(MapImage, map_id)
    if map_row is None or map_row.room_id != room_id:
        raise HTTPException(status_code=404, detail="Карта не найдена")

    file_path = map_row.file_path
    was_active = room.active_map_id == map_row.id
    if was_active:
        # Сначала снимаем ссылку, иначе удаление упрётся во внешний ключ.
        room.active_map_id = None
    db.delete(map_row)
    db.commit()
    delete_upload_if_unused(db, file_path)

    if was_active:
        await manager.broadcast(room_id, {"type": "map_changed", "map": None})


@router.post("/{room_id}/map", response_model=MapOut)
async def upload_map(
    room_id: int,
    file: UploadFile = File(...),
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> MapImage:
    """Мастер загружает картинку карты. Она становится активной картой комнаты."""
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только изображения (png/jpeg/webp/gif)")

    content = await file.read()
    if len(content) > MAX_MAP_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 15 МБ)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    stored_name = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    map_row = MapImage(
        room_id=room.id,
        filename=file.filename or stored_name,
        file_path=f"/uploads/{stored_name}",
        width=0,  # реальные размеры фронтенд определит по загруженной картинке
        height=0,
        uploaded_by=user.id,
    )
    db.add(map_row)
    db.flush()
    room.active_map_id = map_row.id
    db.commit()
    db.refresh(map_row)
    # Раньше новую карту видел только тот, кто её загрузил: остальным она приезжала
    # лишь после перезагрузки страницы. Теперь карта меняется у всех сразу.
    await manager.broadcast(room_id, {"type": "map_changed", "map": _map_payload(map_row)})
    return map_row
