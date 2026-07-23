"""Админ-панель: управление пользователями, персонажами (коды — в routers/codes.py)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AccessCode, DiceRoll, HeroSheet, Room, RoomMember, Token, User
from ..schemas import AdminUserUpdateIn, PasswordResetIn, RoomOut, TokenOut, UserOut
from ..security import hash_password, require_admin
from ..storage import delete_upload_if_unused, delete_uploads_if_unused, room_file_urls

router = APIRouter(prefix="/admin", tags=["admin"])

_VALID_ROLES = {"player", "admin"}


@router.get("/users", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())))


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: AdminUserUpdateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> User:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    fields = data.model_dump(exclude_unset=True)
    if "role" in fields:
        if fields["role"] not in _VALID_ROLES:
            raise HTTPException(status_code=400, detail="Недопустимая роль")
        if target.id == admin.id and fields["role"] != "admin":
            raise HTTPException(status_code=400, detail="Нельзя снять админство с самого себя")
        target.role = fields["role"]
    if "is_dm" in fields:
        target.is_dm = fields["is_dm"]
    if "is_active" in fields:
        if target.id == admin.id and fields["is_active"] is False:
            raise HTTPException(status_code=400, detail="Нельзя заблокировать самого себя")
        target.is_active = fields["is_active"]
    if "subscription_expires_at" in fields:
        target.subscription_expires_at = fields["subscription_expires_at"]

    db.commit()
    db.refresh(target)
    return target


@router.post("/users/{user_id}/reset-password", status_code=204)
def reset_password(
    user_id: int,
    data: PasswordResetIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Сброс пароля пользователю. Почты в проекте нет, поэтому сбрасывает админ,
    а новый пароль передаёт человеку лично (тот меняет его через /auth/change-password)."""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    target.password_hash = hash_password(data.new_password)
    db.commit()


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    # Собираем пути к файлам, которые исчезнут вместе с пользователем: карты и аватары
    # из его комнат плюс портреты его свитков (свитки удалятся каскадом по FK).
    doomed_files: list[str | None] = []
    for room in db.scalars(select(Room).where(Room.dm_id == user_id)).all():
        doomed_files += room_file_urls(db, room.id)
    doomed_files += list(
        db.scalars(select(HeroSheet.portrait_url).where(HeroSheet.owner_user_id == user_id))
    )

    # Аккуратно убираем все ссылки на пользователя, иначе удаление падает
    # на ограничениях внешних ключей (это и вызывало "network error").
    # 1. Комнаты, где он мастер — удаляем целиком (БД каскадно удалит их
    #    участников, персонажей, карты и броски).
    for room in db.scalars(select(Room).where(Room.dm_id == user_id)).all():
        db.delete(room)
    db.flush()

    # 2. Его броски в чужих комнатах.
    db.execute(delete(DiceRoll).where(DiceRoll.user_id == user_id))
    # 3. Его участие в чужих комнатах.
    db.execute(delete(RoomMember).where(RoomMember.user_id == user_id))
    # 4. Фишки, которыми он владел в чужих комнатах — делаем "ничьими".
    db.execute(
        update(Token).where(Token.owner_user_id == user_id).values(owner_user_id=None)
    )
    # 5. Коды, привязанные к нему или созданные им — отвязываем.
    db.execute(
        update(AccessCode).where(AccessCode.assigned_user_id == user_id).values(assigned_user_id=None)
    )
    db.execute(
        update(AccessCode)
        .where(AccessCode.created_by_admin_id == user_id)
        .values(created_by_admin_id=None)
    )

    db.delete(target)
    db.commit()
    delete_uploads_if_unused(db, doomed_files)


@router.get("/rooms", response_model=list[RoomOut])
def all_rooms(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[Room]:
    """Все игровые комнаты (удаление — через DELETE /rooms/{id}, админу разрешено)."""
    return list(db.scalars(select(Room).order_by(Room.created_at.desc())))


@router.get("/tokens", response_model=list[TokenOut])
def all_tokens(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[Token]:
    """Все фишки со всех карт."""
    return list(db.scalars(select(Token).order_by(Token.room_id)))


@router.delete("/tokens/{token_id}", status_code=204)
def delete_token(
    token_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    tk = db.get(Token, token_id)
    if tk is None:
        raise HTTPException(status_code=404, detail="Фишка не найдена")
    avatar = tk.avatar_url
    db.delete(tk)
    db.commit()
    delete_upload_if_unused(db, avatar)
