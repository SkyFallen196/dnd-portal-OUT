"""token z-order

Порядок отрисовки фишек: чем больше z, тем выше фишка лежит. Без этого фишку,
накрытую другой (толпа в дверях, дракон поверх партии), нельзя ни разглядеть,
ни подцепить мышью.

Revision ID: b2e8a5c4d37a
Revises: a1d7f4b3c269
Create Date: 2026-07-23 09:15:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2e8a5c4d37a'
down_revision: Union[str, None] = 'a1d7f4b3c269'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tokens', sa.Column('z', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('tokens', 'z', server_default=None)


def downgrade() -> None:
    op.drop_column('tokens', 'z')
