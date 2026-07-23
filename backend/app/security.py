"""Хеширование паролей, JWT-токены и зависимости для проверки прав."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from .config import settings
from .database import get_db
from .models import User

# FastAPI будет искать токен в заголовке Authorization: Bearer <token>.
# tokenUrl нужен только для кнопки Authorize в Swagger-документации.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


# ---------- Пароли ----------
def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------
def create_access_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Достаёт пользователя из токена. Кидает 401, если токен плохой."""
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить токен",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = int(payload.get("sub"))
    except (jwt.PyJWTError, TypeError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Аккаунт заблокирован")
    return user


def admin_edit_mode(x_admin_edit: str | None = Header(default=None)) -> bool:
    """Включён ли у админа «Режим редактирования».

    Фронтенд шлёт заголовок X-Admin-Edit: 1, когда тумблер включён. Без него админ
    в чужих комнатах — только наблюдатель (модератор), а не мастер.
    """
    return x_admin_edit == "1"


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нужны права администратора")
    return user


def require_active_subscription(user: User = Depends(get_current_user)) -> User:
    """Доступ к игровым функциям — только с активной подпиской (админ проходит всегда)."""
    if user.role == "admin":
        return user
    exp = user.subscription_expires_at
    if exp is None or exp < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Нужна активная подписка. Активируйте код доступа.",
        )
    return user
