"""rename gm to dm

Мастера в D&D называют DM (Dungeon Master), а не GM. Приводим наименования к этому:
- users.is_gm  -> users.is_dm  (может ли водить игры);
- rooms.gm_id  -> rooms.dm_id  (мастер этой комнаты), вместе с внешним ключом.

Переименование колонок и ключа не трогает данные — значения остаются на месте.

Revision ID: 7a4c1e9d5b06
Revises: 6f3b28d5a094
Create Date: 2026-07-23 09:30:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = '7a4c1e9d5b06'
down_revision: Union[str, None] = '6f3b28d5a094'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('users', 'is_gm', new_column_name='is_dm')
    op.alter_column('rooms', 'gm_id', new_column_name='dm_id')
    op.execute('ALTER TABLE rooms RENAME CONSTRAINT rooms_gm_id_fkey TO rooms_dm_id_fkey')


def downgrade() -> None:
    op.execute('ALTER TABLE rooms RENAME CONSTRAINT rooms_dm_id_fkey TO rooms_gm_id_fkey')
    op.alter_column('rooms', 'dm_id', new_column_name='gm_id')
    op.alter_column('users', 'is_dm', new_column_name='is_gm')
