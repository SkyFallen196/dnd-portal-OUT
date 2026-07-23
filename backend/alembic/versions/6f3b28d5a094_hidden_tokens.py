"""hidden tokens

Скрытая фишка видна только мастеру: нужна для засад и монстров, которых партия
ещё не встретила. Прятать на клиенте нельзя — данные не должны доходить до игроков
вообще, поэтому фильтрация идёт на сервере (и в API, и в рассылке WebSocket).

Revision ID: 6f3b28d5a094
Revises: 5e2a91c47f18
Create Date: 2026-07-22 22:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6f3b28d5a094'
down_revision: Union[str, None] = '5e2a91c47f18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # server_default нужен только чтобы заполнить существующие строки; сразу снимаем,
    # значение по умолчанию задаёт модель.
    op.add_column('tokens', sa.Column('hidden', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column('tokens', 'hidden', server_default=None)


def downgrade() -> None:
    op.drop_column('tokens', 'hidden')
