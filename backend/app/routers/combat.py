"""Порядок ходов в бою: начать, передать ход, закончить.

Логика порядка живёт в app/combat.py — она нужна ещё и при удалении фишек.
Любое изменение рассылается всем в комнате событием `combat_updated` с полным
состоянием: состояние маленькое, а слать целиком надёжнее, чем сшивать из кусочков.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..combat import advance_turn, broadcast_combat, combat_order, combat_payload, end_combat
from ..database import get_db
from ..dice_engine import parse_and_roll
from ..models import Room, Token, User
from ..room_access import ensure_dm, ensure_member, get_room_or_404, is_room_dm
from ..schemas import CombatOut, InitiativeIn
from ..security import admin_edit_mode, require_active_subscription

router = APIRouter(prefix="/rooms/{room_id}/combat", tags=["combat"])


async def _apply(db: Session, room: Room, viewer_is_dm: bool) -> dict:
    """Разослать изменение всем и вернуть состояние глазами того, кто вызвал.

    Отдавать вызывающему мастерскую версию нельзя: «следующий ход» может нажать
    и игрок, а в полном состоянии видны скрытые фишки.
    """
    await broadcast_combat(db, room)
    return combat_payload(db, room, for_dm=viewer_is_dm)


@router.get("", response_model=CombatOut)
def get_combat(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> dict:
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    return combat_payload(db, room, for_dm=is_room_dm(room, user, admin_edit))


@router.post("/start", response_model=CombatOut)
async def start_combat(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> dict:
    """Начать бой: бросить d20 инициативы всем фишкам на карте.

    Значения потом можно поправить вручную — в D&D к броску прибавляют модификатор
    ловкости, а его портал не знает.
    """
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    tokens = list(db.scalars(select(Token).where(Token.room_id == room_id)))
    if not tokens:
        raise HTTPException(status_code=400, detail="На карте нет ни одной фишки")

    for t in tokens:
        t.initiative = parse_and_roll("d20", "normal").total

    room.combat_round = 1
    db.flush()
    order = combat_order(db, room_id)
    room.combat_token_id = order[0].id if order else None
    db.commit()
    return await _apply(db, room, is_room_dm(room, user, admin_edit))


@router.post("/next", response_model=CombatOut)
async def next_turn(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> dict:
    """Передать ход следующему.

    Может мастер, а также владелец фишки, чей сейчас ход: закончить свой ход —
    нормальное право игрока, дёргать мастера ради этого не нужно.
    """
    room = get_room_or_404(db, room_id)
    ensure_member(db, room, user)
    if room.combat_round == 0:
        raise HTTPException(status_code=400, detail="Бой не идёт")

    if not is_room_dm(room, user, admin_edit):
        current = db.get(Token, room.combat_token_id) if room.combat_token_id else None
        if current is None or current.owner_user_id != user.id:
            raise HTTPException(status_code=403, detail="Сейчас не ваш ход")

    advance_turn(db, room)
    db.commit()
    return await _apply(db, room, is_room_dm(room, user, admin_edit))


@router.post("/end", response_model=CombatOut)
async def finish_combat(
    room_id: int,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> dict:
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)
    end_combat(db, room)
    db.commit()
    return await _apply(db, room, is_room_dm(room, user, admin_edit))


@router.patch("/tokens/{token_id}", response_model=CombatOut)
async def set_initiative(
    room_id: int,
    token_id: int,
    data: InitiativeIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> dict:
    """Поправить инициативу фишки или убрать её из боя (initiative = null).

    Так же в бой добавляют опоздавших: выставил значение — фишка встала в очередь.
    """
    room = get_room_or_404(db, room_id)
    ensure_dm(room, user, admin_edit)

    token = db.get(Token, token_id)
    if token is None or token.room_id != room_id:
        raise HTTPException(status_code=404, detail="Фишка не найдена")

    token.initiative = data.initiative
    db.flush()

    # Убрали из боя того, чей был ход — передаём ход дальше, иначе бой замрёт.
    if data.initiative is None and room.combat_token_id == token_id:
        advance_turn(db, room)
        if room.combat_token_id == token_id:
            end_combat(db, room)

    db.commit()
    return await _apply(db, room, is_room_dm(room, user, admin_edit))
