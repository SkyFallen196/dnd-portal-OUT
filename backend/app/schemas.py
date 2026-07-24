"""Pydantic-схемы: описывают форму данных на входе и выходе API."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Границы размера фишки. Те же числа зашиты в интерфейсе (DMPanel.tsx),
# но полагаться на интерфейс нельзя: запрос могут прислать и в обход него.
MIN_TOKEN_SIZE = 0.4
MAX_TOKEN_SIZE = 5.0
MAX_HP_VALUE = 100_000
# Сторона клетки сетки в пикселях. 0 — сетка выключена. Верхняя граница —
# защита от опечатки вроде 10000, при которой клиент рисовал бы одну клетку на всю карту.
MAX_GRID_SIZE = 500


# ---------- Auth ----------
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class PasswordChangeIn(BaseModel):
    """Смена своего пароля: нужно знать текущий."""
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class PasswordResetIn(BaseModel):
    """Сброс пароля админом (текущий знать не нужно)."""
    new_password: str = Field(min_length=6, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    email: EmailStr
    role: str  # "player" | "admin"
    is_dm: bool = False  # игровая роль мастера, независима от role
    subscription_expires_at: datetime | None
    is_active: bool
    created_at: datetime


# ---------- Access codes ----------
class CodeCreateIn(BaseModel):
    duration_days: int = Field(default=30, ge=1, le=3650)
    count: int = Field(default=1, ge=1, le=100)  # сколько кодов создать за раз


class CodeActivateIn(BaseModel):
    code: str


class CodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    duration_days: int
    is_activated: bool
    assigned_user_id: int | None
    activated_at: datetime | None
    created_at: datetime


# ---------- Rooms ----------
class RoomCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class RoomJoinIn(BaseModel):
    invite_code: str


class RoomUpdateIn(BaseModel):
    """Настройки комнаты, которые меняет мастер по ходу игры."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    # 0 — выключить сетку. Одна клетка всегда 5 футов.
    grid_size: int | None = Field(default=None, ge=0, le=MAX_GRID_SIZE)


class MemberOut(BaseModel):
    user_id: int
    username: str
    role: str


class MapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    file_path: str
    width: int
    height: int


class RoomOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    dm_id: int
    invite_code: str
    active_map_id: int | None
    grid_size: int = 0  # 0 — сетки нет; иначе сторона клетки (5 футов) в пикселях
    created_at: datetime


class RoomDetailOut(RoomOut):
    members: list[MemberOut] = []
    active_map: MapOut | None = None


# ---------- Tokens (фишки на карте) ----------
class StatusEffect(BaseModel):
    name: str = Field(min_length=1, max_length=40)
    # Literal вместо str: сервер примет только эти два значения, иначе 422.
    type: Literal["buff", "debuff"] = "buff"


class TokenCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    color: str = Field(default="#c0392b", max_length=20)
    x: float = 100.0
    y: float = 100.0
    hp: int = Field(default=10, ge=0, le=MAX_HP_VALUE)
    max_hp: int = Field(default=10, ge=1, le=MAX_HP_VALUE)
    is_npc: bool = False
    hidden: bool = False  # можно сразу поставить фишку скрытой (засада)
    owner_user_id: int | None = None


class TokenUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    color: str | None = Field(default=None, max_length=20)
    x: float | None = None
    y: float | None = None
    hp: int | None = Field(default=None, ge=0, le=MAX_HP_VALUE)
    max_hp: int | None = Field(default=None, ge=1, le=MAX_HP_VALUE)
    size: float | None = Field(default=None, ge=MIN_TOKEN_SIZE, le=MAX_TOKEN_SIZE)
    effects: list[StatusEffect] | None = Field(default=None, max_length=20)
    hidden: bool | None = None  # скрыть фишку от игроков
    z: int | None = None  # порядок отрисовки: больше — выше


class TokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    owner_user_id: int | None
    hero_sheet_id: int | None = None
    name: str
    color: str
    avatar_url: str | None
    x: float
    y: float
    hp: int
    max_hp: int
    is_npc: bool
    size: float = 1.0
    effects: list[StatusEffect] = []
    initiative: int | None = None  # None — фишка не участвует в текущем бою
    hidden: bool = False  # игрокам такие фишки вообще не отдаются
    z: int = 0  # порядок отрисовки на карте


# ---------- Combat (порядок ходов) ----------
class CombatantOut(BaseModel):
    token_id: int
    name: str
    color: str
    initiative: int
    is_npc: bool
    hp: int
    max_hp: int
    owner_user_id: int | None


class CombatOut(BaseModel):
    round: int  # 0 — боя нет
    current_token_id: int | None
    order: list[CombatantOut] = []


class InitiativeIn(BaseModel):
    """Задать инициативу вручную. null — убрать фишку из боя."""
    initiative: int | None = Field(default=None, ge=-20, le=99)


# ---------- Dice ----------
class RollIn(BaseModel):
    formula: str = Field(min_length=1, max_length=100)  # например "2d6+3" или "d20"
    roll_type: str = "normal"  # normal | advantage | disadvantage
    private: bool = False  # скрытый бросок мастера; игроки его не увидят


class RollOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    user_id: int
    username: str  # берётся из свойства DiceRoll.username
    formula: str
    rolls_json: str
    modifier: int
    total: int
    roll_type: str
    private: bool = False
    created_at: datetime


# ---------- Hero sheets (свиток героя) ----------
class HeroSheetIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    race: str = ""
    age: str = ""
    weight: str = ""
    height: str = ""
    crop_position: str = "center"
    strength: int = 10
    dexterity: int = 10
    defense: int = 10
    hp: int = 20
    endurance: int = 10
    wisdom: int = 10
    intelligence: int = 10
    charisma: int = 10
    inventory: list[str] = []
    abilities: list[str] = []
    weaknesses: list[str] = []
    innate_ability: str = ""
    backstory: str = ""


class HeroSheetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_user_id: int
    name: str
    race: str
    age: str
    weight: str
    height: str
    portrait_url: str | None
    crop_position: str
    strength: int
    dexterity: int
    defense: int
    hp: int
    endurance: int
    wisdom: int
    intelligence: int
    charisma: int
    inventory: list[str]
    abilities: list[str]
    weaknesses: list[str]
    innate_ability: str
    backstory: str
    created_at: datetime


class PlaceHeroIn(BaseModel):
    """Выставить свиток героя на карту комнаты как фишку."""
    room_id: int
    x: float = 120.0
    y: float = 120.0
    color: str = "#2980b9"


class HeroSheetSummary(BaseModel):
    """Краткая карточка для списка (в т.ч. список всех героев у DM/админа)."""
    id: int
    owner_user_id: int
    owner_username: str
    name: str
    race: str
    portrait_url: str | None


# ---------- Handouts (заметки и раздаточные материалы) ----------
class HandoutIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(default="", max_length=20_000)
    is_public: bool = False  # по умолчанию материал видит только мастер


class HandoutUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, max_length=20_000)
    is_public: bool | None = None


class HandoutOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    room_id: int
    title: str
    body: str
    image_url: str | None
    is_public: bool
    created_at: datetime


# ---------- Admin ----------
class AdminUserUpdateIn(BaseModel):
    role: str | None = None  # player | admin
    is_dm: bool | None = None  # выдать/забрать роль мастера
    is_active: bool | None = None
    subscription_expires_at: datetime | None = None
