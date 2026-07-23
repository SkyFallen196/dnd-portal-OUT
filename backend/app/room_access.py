"""Вспомогательные проверки доступа к комнате."""
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Room, RoomMember, User


def get_room_or_404(db: Session, room_id: int) -> Room:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Комната не найдена")
    return room


def is_member(db: Session, room: Room, user: User) -> bool:
    """Может ли пользователь ВИДЕТЬ комнату.

    Админ видит любую комнату (режим модератора), даже не будучи участником.
    """
    if user.role == "admin" or room.dm_id == user.id:
        return True
    member = db.scalar(
        select(RoomMember).where(RoomMember.room_id == room.id, RoomMember.user_id == user.id)
    )
    return member is not None


def ensure_member(db: Session, room: Room, user: User) -> None:
    if not is_member(db, room, user):
        raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")


def is_room_dm(room: Room, user: User, admin_edit: bool = False) -> bool:
    """Права мастера В ЭТОЙ комнате.

    Мастер комнаты — всегда. Админ — только когда явно включил «Режим редактирования»
    (иначе он в чужой комнате наблюдатель-модератор).
    """
    if room.dm_id == user.id:
        return True
    return user.role == "admin" and admin_edit


def ensure_dm(room: Room, user: User, admin_edit: bool = False) -> None:
    if is_room_dm(room, user, admin_edit):
        return
    if user.role == "admin":
        raise HTTPException(
            status_code=403,
            detail="Вы в чужой комнате как наблюдатель. Включите «Режим редактирования», чтобы менять игру.",
        )
    raise HTTPException(status_code=403, detail="Только мастер комнаты может это делать")
