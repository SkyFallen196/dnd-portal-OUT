"""private DM rolls

Приватный бросок мастера: скрытая проверка, о которой партия не должна знать.
Игрокам такие записи не отдаются ни в истории, ни по WebSocket — фильтрует сервер.

Revision ID: 8b5d2f1a3c47
Revises: 7a4c1e9d5b06
Create Date: 2026-07-23 09:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '8b5d2f1a3c47'
down_revision: Union[str, None] = '7a4c1e9d5b06'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default нужен только чтобы заполнить существующие строки; сразу снимаем,
    # значение по умолчанию задаёт модель.
    op.add_column('dice_rolls', sa.Column('private', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('dice_rolls', 'private', server_default=None)


def downgrade() -> None:
    op.drop_column('dice_rolls', 'private')
