"""room grid size

Сторона клетки сетки в пикселях карты (0 — сетки нет). Хранится у комнаты, а не
у клиента: масштаб задаёт мастер под конкретную карту, и линейка должна мерить
одинаково у всех за столом.

Revision ID: 9c6e3a2b4d58
Revises: 8b5d2f1a3c47
Create Date: 2026-07-23 09:05:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '9c6e3a2b4d58'
down_revision: Union[str, None] = '8b5d2f1a3c47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('rooms', sa.Column('grid_size', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('rooms', 'grid_size', server_default=None)


def downgrade() -> None:
    op.drop_column('rooms', 'grid_size')
