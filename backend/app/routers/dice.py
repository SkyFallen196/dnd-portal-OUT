"""Броски костей и журнал бросков."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..dice_engine import parse_and_roll
from ..models import DiceRoll, User
from ..room_access import ensure_member, get_room_or_404
from ..schemas import RollIn, RollOut
from ..security import require_active_subscription
from ..ws_manager import manager

router = APIRouter(prefix="/rooms/{room_id}", tags=["dice"])


@router.get("/rolls", response_model=list[RollOut])
def roll_history(
    room_id: int,
    limit: int = 50,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> list[DiceRoll]:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    limit = max(1, min(limit, 200))
    rows = db.scalars(
        select(DiceRoll)
        # Подтягиваем авторов одним запросом: иначе на 50 бросков ушло бы 50 запросов
        # за именами (журнал показывает, кто бросал).
        .options(selectinload(DiceRoll.user))
        .where(DiceRoll.room_id == room_id)
        .order_by(DiceRoll.created_at.desc())
        .limit(limit)
    )
    return list(reversed(list(rows)))  # старые сверху, новые снизу


@router.post("/roll", response_model=RollOut)
async def make_roll(
    room_id: int,
    data: RollIn,
    user: User = Depends(require_active_subscription),
    db: Session = Depends(get_db),
) -> DiceRoll:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)

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
    )
    db.add(row)
    db.commit()
    db.refresh(row)

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
                "created_at": row.created_at.isoformat(),
            },
        },
    )
    return row
