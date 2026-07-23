"""rename characters to tokens

В проекте было два разных «персонажа»: HeroSheet (свиток — лист персонажа) и Character
(кружок на карте). Из-за одинакового слова код читался тяжело. Кружок теперь называется
фишкой — Token, таблица characters переименована в tokens.

Переименование не трогает данные: PostgreSQL меняет только имена таблицы, ключей и
последовательности, строки остаются на месте.

Revision ID: 4d17f2c8b930
Revises: 3c91d0a7e512
Create Date: 2026-07-22 19:10:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = '4d17f2c8b930'
down_revision: Union[str, None] = '3c91d0a7e512'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Старое имя ключа -> новое. Переименовываем и их, иначе в базе останутся
# ограничения с именами вида characters_*, и через полгода будет непонятно, откуда они.
_CONSTRAINTS = {
    "characters_pkey": "tokens_pkey",
    "characters_room_id_fkey": "tokens_room_id_fkey",
    "characters_owner_user_id_fkey": "tokens_owner_user_id_fkey",
    "characters_hero_sheet_id_fkey": "tokens_hero_sheet_id_fkey",
}


def upgrade() -> None:
    op.rename_table("characters", "tokens")
    op.execute("ALTER SEQUENCE characters_id_seq RENAME TO tokens_id_seq")
    for old, new in _CONSTRAINTS.items():
        op.execute(f"ALTER TABLE tokens RENAME CONSTRAINT {old} TO {new}")


def downgrade() -> None:
    for old, new in _CONSTRAINTS.items():
        op.execute(f"ALTER TABLE tokens RENAME CONSTRAINT {new} TO {old}")
    op.execute("ALTER SEQUENCE tokens_id_seq RENAME TO characters_id_seq")
    op.rename_table("tokens", "characters")
