"""combat initiative

Порядок ходов в бою:
- tokens.initiative — значение инициативы фишки (NULL = не участвует в бою);
- rooms.combat_round — номер раунда (0 = боя нет);
- rooms.combat_token_id — чья сейчас очередь.

Связь rooms -> tokens добавляется отдельным ALTER TABLE: между этими таблицами уже есть
ссылка в обратную сторону (tokens.room_id), то есть получается круг — как с картами.
ON DELETE SET NULL: если фишку убрали с карты прямо в её ход, комната не ломается.

Revision ID: 5e2a91c47f18
Revises: 4d17f2c8b930
Create Date: 2026-07-22 21:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5e2a91c47f18'
down_revision: Union[str, None] = '4d17f2c8b930'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tokens', sa.Column('initiative', sa.Integer(), nullable=True))

    # server_default нужен только чтобы заполнить уже существующие строки: у комнат,
    # созданных до этой миграции, боя нет. Сразу после снимаем — значение по умолчанию
    # задаёт модель (как и у остальных полей проекта).
    op.add_column('rooms', sa.Column('combat_round', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('rooms', 'combat_round', server_default=None)

    op.add_column('rooms', sa.Column('combat_token_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'rooms_combat_token_id_fkey', 'rooms', 'tokens', ['combat_token_id'], ['id'],
        ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('rooms_combat_token_id_fkey', 'rooms', type_='foreignkey')
    op.drop_column('rooms', 'combat_token_id')
    op.drop_column('rooms', 'combat_round')
    op.drop_column('tokens', 'initiative')
