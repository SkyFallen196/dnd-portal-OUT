"""WebSocket-эндпоинт комнаты: реалтайм-перемещение фишек."""
import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..config import settings
from ..database import SessionLocal
from ..models import Room, RoomMember, Token, User
from ..ws_manager import manager

router = APIRouter()


def _authenticate(token: str) -> int | None:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError):
        return None


@router.websocket("/ws/rooms/{room_id}")
async def room_socket(
    websocket: WebSocket, room_id: int, token: str = "", admin_edit: str = ""
) -> None:
    """Клиент подключается: ws://.../ws/rooms/5?token=JWT

    Принимает сообщения вида {"type": "move", "token_id": 1, "x": 120, "y": 80}
    и рассылает всем в комнате событие token_moved.

    admin_edit=1 — админ включил «Режим редактирования» и хочет права мастера.
    """
    user_id = _authenticate(token)
    if user_id is None:
        await websocket.close(code=4401)  # unauthorized
        return

    # Проверяем, что пользователь имеет доступ к комнате.
    db = SessionLocal()
    try:
        user = db.get(User, user_id)
        room = db.get(Room, room_id)
        if user is None or room is None or not user.is_active:
            await websocket.close(code=4404)
            return
        # Права мастера: мастер комнаты всегда; админ — только с режимом редактирования.
        is_dm = room.dm_id == user.id or (user.role == "admin" and admin_edit == "1")
        # Смотреть (подключиться) админ может всегда — как модератор.
        is_member = (
            is_dm
            or user.role == "admin"
            or db.query(RoomMember).filter_by(room_id=room_id, user_id=user_id).first()
        )
        if not is_member:
            await websocket.close(code=4403)
            return
    finally:
        db.close()

    # is_dm запоминается на соединении: по нему решается, кому уходят скрытые фишки.
    # При переключении «Режима редактирования» фронтенд переподключает сокет заново.
    await manager.connect(room_id, websocket, is_dm=is_dm)
    try:
        while True:
            data = await websocket.receive_json()
            if data.get("type") == "move":
                await _handle_move(room_id, user_id, is_dm, data, websocket)
    except WebSocketDisconnect:
        await manager.disconnect(room_id, websocket)
    except Exception:
        await manager.disconnect(room_id, websocket)


async def _handle_move(room_id: int, user_id: int, is_dm: bool, data: dict, sender: WebSocket) -> None:
    token_id = data.get("token_id")
    x, y = data.get("x"), data.get("y")
    if token_id is None or x is None or y is None:
        return

    db = SessionLocal()
    try:
        tk = db.get(Token, token_id)
        if tk is None or tk.room_id != room_id:
            return
        # Двигать можно свою фишку или любую — если ты мастер.
        if not is_dm and tk.owner_user_id != user_id:
            return
        tk.x = float(x)
        tk.y = float(y)
        db.commit()
    finally:
        db.close()

    await manager.broadcast(
        room_id,
        {"type": "token_moved", "token": {"id": token_id, "x": float(x), "y": float(y)}},
    )
