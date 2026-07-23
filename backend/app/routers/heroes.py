"""Свитки героев — личные листы персонажей игроков.

Про подписку. Сами свитки доступны сразу после регистрации, без активного кода:
человек может завести героя и заполнить его, пока ждёт доступ к игре. А вот выставить
героя на карту (`POST /heroes/{id}/place`) — это уже действие внутри игровой комнаты,
наравне с созданием фишек и бросками костей, поэтому там подписка обязательна.
"""
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HeroSheet, Room, RoomMember, Token, User
from ..room_access import get_room_or_404, is_member, is_room_dm
from ..schemas import HeroSheetIn, HeroSheetOut, HeroSheetSummary, PlaceHeroIn, TokenOut
from ..security import admin_edit_mode, get_current_user, require_active_subscription
from ..storage import delete_upload_if_unused
from ..ws_manager import manager
from .tokens import token_payload

router = APIRouter(prefix="/heroes", tags=["heroes"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_PORTRAIT_BYTES = 5 * 1024 * 1024  # 5 МБ

_FIELDS = (
    "name", "race", "age", "weight", "height", "crop_position",
    "strength", "dexterity", "defense", "hp", "endurance", "wisdom",
    "intelligence", "charisma", "inventory", "abilities", "weaknesses",
    "innate_ability", "backstory",
)


def _get_or_404(db: Session, hero_id: int) -> HeroSheet:
    hero = db.get(HeroSheet, hero_id)
    if hero is None:
        raise HTTPException(status_code=404, detail="Свиток не найден")
    return hero


def _dm_sees_player(db: Session, dm: User, owner_id: int) -> bool:
    """Мастер видит свитки только тех игроков, кто состоит в ЕГО комнатах."""
    if not dm.is_dm:
        return False
    found = db.scalar(
        select(RoomMember.id)
        .join(Room, Room.id == RoomMember.room_id)
        .where(Room.dm_id == dm.id, RoomMember.user_id == owner_id)
        .limit(1)
    )
    return found is not None


def _can_view(db: Session, hero: HeroSheet, user: User) -> bool:
    if hero.owner_user_id == user.id or user.role == "admin":
        return True
    return _dm_sees_player(db, user, hero.owner_user_id)


def _can_edit(hero: HeroSheet, user: User) -> bool:
    return hero.owner_user_id == user.id or user.role == "admin"


async def _sync_tokens(db: Session, hero: HeroSheet) -> None:
    """Свиток — источник правды: обновляем фишки, выставленные из него.

    Синхронизируем имя, портрет и максимум HP. Текущее HP остаётся боевым
    состоянием фишки, но не может превышать новый максимум.
    """
    tokens = list(db.scalars(select(Token).where(Token.hero_sheet_id == hero.id)))
    if not tokens:
        return

    for tk in tokens:
        tk.name = hero.name
        tk.avatar_url = hero.portrait_url
        tk.max_hp = hero.hp
        if tk.hp > hero.hp:
            tk.hp = hero.hp
    db.commit()

    for tk in tokens:
        db.refresh(tk)
        await manager.broadcast(
            tk.room_id, {"type": "token_updated", "token": token_payload(tk)}
        )


@router.get("", response_model=list[HeroSheetOut])
def my_heroes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[HeroSheet]:
    """Мои свитки."""
    return list(
        db.scalars(
            select(HeroSheet).where(HeroSheet.owner_user_id == user.id).order_by(HeroSheet.created_at)
        )
    )


@router.get("/all", response_model=list[HeroSheetSummary])
def all_heroes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[HeroSheetSummary]:
    """Свитки игроков: админу — все, мастеру — только игроков из его комнат."""
    if user.role == "admin":
        rows = db.scalars(select(HeroSheet).order_by(HeroSheet.name)).all()
    elif user.is_dm:
        my_players = select(RoomMember.user_id).join(Room, Room.id == RoomMember.room_id).where(
            Room.dm_id == user.id
        )
        rows = db.scalars(
            select(HeroSheet)
            .where(HeroSheet.owner_user_id.in_(my_players))
            .order_by(HeroSheet.name)
        ).all()
    else:
        raise HTTPException(status_code=403, detail="Доступно только мастеру или админу")
    owners = {u.id: u.username for u in db.scalars(select(User))}
    return [
        HeroSheetSummary(
            id=h.id,
            owner_user_id=h.owner_user_id,
            owner_username=owners.get(h.owner_user_id, f"#{h.owner_user_id}"),
            name=h.name,
            race=h.race,
            portrait_url=h.portrait_url,
        )
        for h in rows
    ]


@router.post("", response_model=HeroSheetOut, status_code=201)
def create_hero(
    data: HeroSheetIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HeroSheet:
    hero = HeroSheet(owner_user_id=user.id, **data.model_dump())
    db.add(hero)
    db.commit()
    db.refresh(hero)
    return hero


@router.get("/{hero_id}", response_model=HeroSheetOut)
def get_hero(
    hero_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HeroSheet:
    hero = _get_or_404(db, hero_id)
    if not _can_view(db, hero, user):
        raise HTTPException(status_code=403, detail="Нет доступа к этому свитку")
    return hero


@router.put("/{hero_id}", response_model=HeroSheetOut)
async def update_hero(
    hero_id: int,
    data: HeroSheetIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HeroSheet:
    hero = _get_or_404(db, hero_id)
    if not _can_edit(hero, user):
        raise HTTPException(status_code=403, detail="Можно редактировать только свой свиток")
    for field, value in data.model_dump().items():
        setattr(hero, field, value)
    db.commit()
    db.refresh(hero)
    await _sync_tokens(db, hero)  # подтягиваем изменения в фишки на картах
    return hero


@router.delete("/{hero_id}", status_code=204)
def delete_hero(
    hero_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    hero = _get_or_404(db, hero_id)
    if not _can_edit(hero, user):
        raise HTTPException(status_code=403, detail="Можно удалить только свой свиток")
    portrait = hero.portrait_url
    db.delete(hero)
    db.commit()
    # Портрет стираем, только если он не остался аватаром выставленной фишки.
    delete_upload_if_unused(db, portrait)


@router.post("/{hero_id}/place", response_model=TokenOut, status_code=201)
async def place_on_map(
    hero_id: int,
    data: PlaceHeroIn,
    user: User = Depends(require_active_subscription),
    admin_edit: bool = Depends(admin_edit_mode),
    db: Session = Depends(get_db),
) -> Token:
    """Выставить свиток на карту комнаты — создаёт фишку с именем, портретом и HP героя.

    Игровое действие, поэтому нужна активная подписка (см. пояснение вверху файла).
    """
    hero = _get_or_404(db, hero_id)
    room = get_room_or_404(db, data.room_id)

    # Выставлять может владелец свитка или мастер этой комнаты
    # (админ — только с включённым «Режимом редактирования»).
    is_dm = is_room_dm(room, user, admin_edit)
    if hero.owner_user_id != user.id and not is_dm:
        raise HTTPException(status_code=403, detail="Можно выставлять только свой свиток")

    # И тот, кто выставляет, и владелец героя должны быть участниками комнаты.
    if not is_member(db, room, user):
        raise HTTPException(status_code=403, detail="Вы не участник этой комнаты")
    owner = db.get(User, hero.owner_user_id)
    if owner is None or not is_member(db, room, owner):
        raise HTTPException(status_code=400, detail="Владелец героя не состоит в этой комнате")

    # Один и тот же свиток не выставляем в комнату дважды.
    exists = db.scalar(
        select(Token).where(Token.room_id == room.id, Token.hero_sheet_id == hero.id)
    )
    if exists is not None:
        raise HTTPException(status_code=400, detail="Этот герой уже стоит на карте этой комнаты")

    tk = Token(
        room_id=room.id,
        owner_user_id=hero.owner_user_id,
        hero_sheet_id=hero.id,
        name=hero.name,
        color=data.color,
        avatar_url=hero.portrait_url,
        x=data.x,
        y=data.y,
        hp=hero.hp,
        max_hp=hero.hp,
        is_npc=False,
    )
    db.add(tk)
    db.commit()
    db.refresh(tk)

    await manager.broadcast(room.id, {"type": "token_added", "token": token_payload(tk)})
    return tk


@router.post("/{hero_id}/portrait", response_model=HeroSheetOut)
async def upload_portrait(
    hero_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HeroSheet:
    hero = _get_or_404(db, hero_id)
    if not _can_edit(hero, user):
        raise HTTPException(status_code=403, detail="Можно менять только свой свиток")

    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только изображения (png/jpeg/webp/gif)")
    content = await file.read()
    if len(content) > MAX_PORTRAIT_BYTES:
        raise HTTPException(status_code=400, detail="Файл слишком большой (максимум 5 МБ)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    stored_name = f"portrait_{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, stored_name), "wb") as f:
        f.write(content)

    old_portrait = hero.portrait_url
    hero.portrait_url = f"/uploads/{stored_name}"
    db.commit()
    db.refresh(hero)
    await _sync_tokens(db, hero)  # новый портрет — и на фишках тоже
    # Старый файл убираем только после синхронизации: до неё на него ещё ссылаются фишки.
    delete_upload_if_unused(db, old_portrait)
    return hero
