"""Броски костей и журнал бросков."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dice_engine import parse_and_roll
from ..models import DiceRoll, User
from ..room_access import ensure_member, get_room_or_404, is_room_dm
from ..schemas import RollIn, RollOut
from ..security import admin_edit_mode, require_active_subscription
from ..ws_manager import manager

router = APIRouter(prefix="/rooms/{room_id}", tags=["dice"])


@router.get("/rolls", response_model=list[RollOut])
def roll_history(
    room_id: int,
    limit: int = 50,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> list[DiceRoll]:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    limit = max(1, min(limit, 200))
    query = (
        select(DiceRoll)
        # Подтягиваем авторов одним запросом: иначе на 50 бросков ушло бы 50 запросов
        # за именами (журнал показывает, кто бросал).
        .options(selectinload(DiceRoll.user))
        .where(DiceRoll.room_id == room_id)
    )
    if not is_room_dm(room, user, admin_edit):
        query = query.where(DiceRoll.private.is_(False))
    rows = db.scalars(query.order_by(DiceRoll.created_at.desc()).limit(limit))
    return list(reversed(list(rows)))  # старые сверху, новые снизу


@router.post("/roll", response_model=RollOut)
async def make_roll(
    room_id: int,
    data: RollIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> DiceRoll:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)

    # Скрытый бросок — инструмент мастера. Игроку он не нужен и ломал бы доверие
    # за столом: партия не должна иметь возможности кидать «в тайне» друг от друга.
    if data.private and not is_room_dm(room, user, admin_edit):
        raise HTTPException(status_code=403, detail="Скрытый бросок доступен только мастеру комнаты")

    try:
        result = parse_and_roll(data.formula, data.roll_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    row = DiceRoll(
        room_id=room_id,
        user_id=user.id,
        formula=result.formula,
        rolls_json=json.dumps(result.rolls),
        modifier=result.modifier,
        total=result.total,
        roll_type=result.roll_type,
        private=data.private,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # Приватный бросок уходит только мастерам — как и скрытые фишки, он не должен
    # доходить до игроков вообще, иначе его видно в инструментах разработчика.
    await manager.broadcast(
        room_id,
        {
            "type": "dice_rolled",
            "roll": {
                "id": row.id,
                "room_id": row.room_id,
                "user_id": row.user_id,
                "username": user.username,
                "formula": row.formula,
                "rolls_json": row.rolls_json,
                "modifier": row.modifier,
                "total": row.total,
                "roll_type": row.roll_type,
                "private": row.private,
                "created_at": row.created_at.isoformat(),
            },
        },
        dm_only=row.private,
    )
    return row
