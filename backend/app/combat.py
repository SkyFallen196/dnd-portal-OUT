"""Порядок ходов в бою (инициатива).

Отдельный модуль, а не только роутер: эти функции нужны ещё и в местах, где фишки
исчезают с карты (удаление фишки, выход игрока из комнаты) — бой не должен ломаться,
если убрали того, чей сейчас ход.

Модель хранения намеренно простая, без отдельной таблицы «участников боя»:
- `tokens.initiative` — значение инициативы (None = фишка не в бою);
- `rooms.combat_round` — номер раунда (0 = боя нет);
- `rooms.combat_token_id` — чей сейчас ход.
Порядок = все фишки комнаты с непустой инициативой, по убыванию. При равной инициативе
(в D&D это обычное дело) порядок стабильный — по id, то есть по времени появления фишки.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Room, Token
from .ws_manager import manager


def combat_order(db: Session, room_id: int) -> list[Token]:
    """Фишки в порядке хода."""
    return list(
        db.scalars(
            select(Token)
            .where(Token.room_id == room_id, Token.initiative.is_not(None))
            .order_by(Token.initiative.desc(), Token.id)
        )
    )


def combat_payload(db: Session, room: Room, for_dm: bool = True) -> dict:
    """Полное состояние боя — уходит и в ответ API, и в WebSocket-событие.

    Игрокам скрытые фишки не показываем даже в очереди ходов: иначе засада
    выдала бы себя строчкой в списке. Если ходит скрытый — игроки просто видят,
    что очередь не на них (current_token_id = None).
    """
    order = combat_order(db, room.id)
    current_id = room.combat_token_id
    if not for_dm:
        hidden_ids = {t.id for t in order if t.hidden}
        order = [t for t in order if not t.hidden]
        if current_id in hidden_ids:
            current_id = None
    return {
        "round": room.combat_round,
        "current_token_id": current_id,
        "order": [
            {
                "token_id": t.id,
                "name": t.name,
                "color": t.color,
                "initiative": t.initiative,
                "is_npc": t.is_npc,
                "hp": t.hp,
                "max_hp": t.max_hp,
                "owner_user_id": t.owner_user_id,
            }
            for t in order
        ],
    }


async def broadcast_combat(db: Session, room: Room) -> None:
    """Разослать состояние боя: мастеру целиком, игрокам — без скрытых фишек.

    Общий помощник: состояние боя меняется не только в своём роутере, но и когда
    фишку удаляют с карты или игрок выходит из комнаты.
    """
    await manager.broadcast_split(
        room.id,
        {"type": "combat_updated", "combat": combat_payload(db, room, for_dm=True)},
        {"type": "combat_updated", "combat": combat_payload(db, room, for_dm=False)},
    )


def advance_turn(db: Session, room: Room) -> None:
    """Передать ход следующему. При обороте круга увеличивается номер раунда.

    Не коммитит — вызывающий сам решает, когда сохранять.
    """
    order = combat_order(db, room.id)
    if not order:
        end_combat(db, room)
        return

    ids = [t.id for t in order]
    if room.combat_token_id not in ids:
        # Текущей фишки больше нет (например, её убрали с карты в её же ход).
        # Продолжаем с начала круга, раунд при этом не накручиваем.
        room.combat_token_id = ids[0]
        return

    i = ids.index(room.combat_token_id)
    if i + 1 < len(ids):
        room.combat_token_id = ids[i + 1]
    else:
        room.combat_token_id = ids[0]
        room.combat_round += 1


def drop_from_combat(db: Session, room: Room, token_ids: list[int]) -> bool:
    """Убрать фишки из боя (их удаляют с карты).

    Если уходит та, чей сейчас ход, — сначала передаём ход дальше, иначе бой замрёт.
    Возвращает True, если состояние боя изменилось (нужно разослать событие).
    """
    if room.combat_round == 0 or not token_ids:
        return False
    if room.combat_token_id in token_ids:
        advance_turn(db, room)
        # Если после передачи хода указатель всё ещё на уходящей фишке — значит,
        # других участников не осталось и бой пора закончить.
        if room.combat_token_id in token_ids:
            end_combat(db, room)
    return True


def end_combat(db: Session, room: Room) -> None:
    """Закончить бой: сбросить инициативу у всех фишек комнаты. Не коммитит."""
    for t in db.scalars(select(Token).where(Token.room_id == room.id)):
        t.initiative = None
    room.combat_round = 0
    room.combat_token_id = None
