"""Регистрация и вход."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User
from ..schemas import PasswordChangeIn, RegisterIn, Token, UserOut
from ..security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(data: RegisterIn, db: Session = Depends(get_db)) -> Token:
    exists = db.scalar(
        select(User).where((User.username == data.username) | (User.email == data.email))
    )
    if exists:
        raise HTTPException(status_code=400, detail="Пользователь с таким именем или email уже есть")

    user = User(
        username=data.username,
        email=data.email,
        password_hash=hash_password(data.password),
        role="player",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return Token(access_token=create_access_token(user.id))


@router.post("/login", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> Token:
    """Вход. Поле username в форме может быть именем ИЛИ email."""
    user = db.scalar(
        select(User).where((User.username == form.username) | (User.email == form.username))
    )
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Аккаунт заблокирован")
    return Token(access_token=create_access_token(user.id))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", response_model=Token)
def change_password(
    data: PasswordChangeIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Token:
    """Смена своего пароля. Нужно подтвердить текущий."""
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль неверный")
    if data.current_password == data.new_password:
        raise HTTPException(status_code=400, detail="Новый пароль совпадает со старым")

    user.password_hash = hash_password(data.new_password)
    db.commit()
    # Старый токен формально ещё жив до истечения срока; выдаём свежий,
    # чтобы фронтенд заменил его сразу после смены пароля.
    return Token(access_token=create_access_token(user.id))
