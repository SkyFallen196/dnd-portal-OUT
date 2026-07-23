"""Коды-подписки: создание (админ) и активация (пользователь)."""
import secrets
import string
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AccessCode, User
from ..schemas import CodeActivateIn, CodeCreateIn, CodeOut, UserOut
from ..security import get_current_user, require_admin

router = APIRouter(prefix="/codes", tags=["codes"])

_ALPHABET = string.ascii_uppercase + string.digits


def _generate_code(length: int = 8) -> str:
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))


@router.post("", response_model=list[CodeOut])
def create_codes(
    data: CodeCreateIn,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[AccessCode]:
    """Админ создаёт один или несколько кодов на N дней."""
    created: list[AccessCode] = []
    for _ in range(data.count):
        # Гарантируем уникальность кода.
        code = _generate_code()
        while db.scalar(select(AccessCode).where(AccessCode.code == code)):
            code = _generate_code()
        obj = AccessCode(
            code=code,
            created_by_admin_id=admin.id,
            duration_days=data.duration_days,
        )
        db.add(obj)
        created.append(obj)
    db.commit()
    for obj in created:
        db.refresh(obj)
    return created


@router.get("", response_model=list[CodeOut])
def list_codes(admin: User = Depends(require_admin), db: Session = Depends(get_db)) -> list[AccessCode]:
    return list(db.scalars(select(AccessCode).order_by(AccessCode.created_at.desc())))


@router.post("/activate", response_model=UserOut)
def activate_code(
    data: CodeActivateIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Пользователь вводит код -> получает подписку на duration_days дней."""
    code = db.scalar(select(AccessCode).where(AccessCode.code == data.code.strip().upper()))
    if code is None:
        raise HTTPException(status_code=404, detail="Код не найден")
    if code.is_activated:
        raise HTTPException(status_code=400, detail="Этот код уже использован")

    now = datetime.now(timezone.utc)
    # Если подписка ещё активна — продлеваем от её конца, иначе от текущего момента.
    base = user.subscription_expires_at
    start = base if (base and base > now) else now
    user.subscription_expires_at = start + timedelta(days=code.duration_days)

    code.is_activated = True
    code.assigned_user_id = user.id
    code.activated_at = now

    db.commit()
    db.refresh(user)
    return user


@router.delete("/{code_id}", status_code=204)
def delete_code(
    code_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    """Удалить код доступа.

    Если код был активирован — вычитаем из подписки привязанного пользователя ровно
    столько дней, сколько давал этот код. Если после вычитания срок уже в прошлом —
    подписка считается законченной (subscription_expires_at = None).
    """
    code = db.get(AccessCode, code_id)
    if code is None:
        raise HTTPException(status_code=404, detail="Код не найден")

    if code.is_activated and code.assigned_user_id:
        user = db.get(User, code.assigned_user_id)
        if user is not None and user.subscription_expires_at is not None:
            new_expiry = user.subscription_expires_at - timedelta(days=code.duration_days)
            now = datetime.now(timezone.utc)
            user.subscription_expires_at = new_expiry if new_expiry > now else None

    db.delete(code)
    db.commit()
