"""ORM-модели = таблицы в базе данных."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # Платформенная роль: "player" | "admin"
    role: Mapped[str] = mapped_column(String(20), default="player")
    # Игровая роль: может ли водить игры (создавать комнаты). Независима от role,
    # поэтому один человек может быть одновременно и админом, и мастером.
    is_dm: Mapped[bool] = mapped_column(Boolean, default=False)
    # До какого момента активна подписка (None = нет доступа к игре).
    subscription_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccessCode(Base):
    """Код-подписка: даёт доступ к порталу на duration_days дней."""
    __tablename__ = "access_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    created_by_admin_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    is_activated: Mapped[bool] = mapped_column(Boolean, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    assigned_user: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_user_id])


class Room(Base):
    """Игровая комната (стол). Создаётся мастером."""
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    dm_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    invite_code: Mapped[str] = mapped_column(String(12), unique=True, index=True)
    active_map_id: Mapped[int | None] = mapped_column(ForeignKey("maps.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Состояние боя. 0 — боя нет, иначе номер текущего раунда.
    combat_round: Mapped[int] = mapped_column(Integer, default=0)
    # Чья сейчас очередь ходить. None — бой не идёт (или фишку убрали с карты).
    combat_token_id: Mapped[int | None] = mapped_column(
        ForeignKey("tokens.id", ondelete="SET NULL"), nullable=True
    )

    members: Mapped[list["RoomMember"]] = relationship(
        "RoomMember", back_populates="room", cascade="all, delete-orphan"
    )
    # foreign_keys указан явно: между rooms и tokens ДВА внешних ключа
    # (tokens.room_id и rooms.combat_token_id), и без подсказки SQLAlchemy
    # не может понять, по какому из них строить связь.
    tokens: Mapped[list["Token"]] = relationship(
        "Token",
        back_populates="room",
        cascade="all, delete-orphan",
        foreign_keys="Token.room_id",
    )


class RoomMember(Base):
    __tablename__ = "room_members"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))

    room: Mapped["Room"] = relationship("Room", back_populates="members")
    user: Mapped["User"] = relationship("User")


class MapImage(Base):
    """Загруженная карта (картинка)."""
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    filename: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(500))  # относительный url, например /uploads/xxx.png
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Token(Base):
    """Фишка на карте — кружок, который двигают мышью (персонаж игрока или NPC мастера).

    Не путать с HeroSheet: свиток — это лист персонажа с характеристиками и историей,
    а фишка — его присутствие на конкретной карте конкретной комнаты. Один свиток может
    стоять фишками сразу в нескольких комнатах, а фишка может существовать и без свитка
    (например, NPC, которого мастер создал прямо на карте).
    """
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    owner_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)  # None = NPC
    # Если фишка выставлена из свитка героя — ссылка на него (иначе None).
    hero_sheet_id: Mapped[int | None] = mapped_column(
        ForeignKey("hero_sheets.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(80))
    color: Mapped[str] = mapped_column(String(20), default="#c0392b")
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    x: Mapped[float] = mapped_column(Float, default=100.0)
    y: Mapped[float] = mapped_column(Float, default=100.0)
    hp: Mapped[int] = mapped_column(Integer, default=10)
    max_hp: Mapped[int] = mapped_column(Integer, default=10)
    is_npc: Mapped[bool] = mapped_column(Boolean, default=False)
    # Множитель размера фишки (1.0 = базовый радиус). Меняет только мастер.
    size: Mapped[float] = mapped_column(Float, default=1.0)
    # Баффы/дебаффы: список объектов {"name": str, "type": "buff"|"debuff"}.
    effects: Mapped[list] = mapped_column(JSON, default=list)
    # Инициатива в текущем бою. None — фишка в бою не участвует.
    initiative: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Скрытая фишка видна только мастеру (засады, ещё не встреченные монстры).
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    room: Mapped["Room"] = relationship("Room", back_populates="tokens", foreign_keys=[room_id])


class HeroSheet(Base):
    """Свиток героя — личный лист персонажа игрока (характеристики, инвентарь, история).

    На карту он попадает в виде фишки — см. Token.
    """
    __tablename__ = "hero_sheets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # Основное
    name: Mapped[str] = mapped_column(String(80))
    race: Mapped[str] = mapped_column(String(60), default="")
    age: Mapped[str] = mapped_column(String(20), default="")
    weight: Mapped[str] = mapped_column(String(20), default="")
    height: Mapped[str] = mapped_column(String(20), default="")
    portrait_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    crop_position: Mapped[str] = mapped_column(String(10), default="center")  # center|top|bottom|left|right

    # Характеристики
    strength: Mapped[int] = mapped_column(Integer, default=10)
    dexterity: Mapped[int] = mapped_column(Integer, default=10)
    defense: Mapped[int] = mapped_column(Integer, default=10)
    hp: Mapped[int] = mapped_column(Integer, default=20)
    endurance: Mapped[int] = mapped_column(Integer, default=10)
    wisdom: Mapped[int] = mapped_column(Integer, default=10)
    intelligence: Mapped[int] = mapped_column(Integer, default=10)
    charisma: Mapped[int] = mapped_column(Integer, default=10)

    # Списки (строки) и тексты
    inventory: Mapped[list] = mapped_column(JSON, default=list)
    abilities: Mapped[list] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list] = mapped_column(JSON, default=list)
    innate_ability: Mapped[str] = mapped_column(String(200), default="")
    backstory: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class DiceRoll(Base):
    """Запись броска костей (журнал)."""
    __tablename__ = "dice_rolls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    formula: Mapped[str] = mapped_column(String(100))
    rolls_json: Mapped[str] = mapped_column(Text)  # список выпавших значений в JSON
    modifier: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    roll_type: Mapped[str] = mapped_column(String(20), default="normal")  # normal|advantage|disadvantage
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship("User")

    @property
    def username(self) -> str:
        """Имя бросавшего — журнал должен показывать имя, а не «#57».

        Пользователя могли удалить (его броски тогда тоже удаляются, но подстрахуемся).
        """
        return self.user.username if self.user is not None else f"#{self.user_id}"
