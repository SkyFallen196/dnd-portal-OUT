"""handouts

Заметки и раздаточные материалы комнаты: мастер готовит их заранее и открывает
партии по ходу игры. Пока is_public выключен, материал видит только мастер.

Revision ID: a1d7f4b3c269
Revises: 9c6e3a2b4d58
Create Date: 2026-07-23 09:10:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1d7f4b3c269'
down_revision: Union[str, None] = '9c6e3a2b4d58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'handouts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=120), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('is_public', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_handouts_room_id'), 'handouts', ['room_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_handouts_room_id'), table_name='handouts')
    op.drop_table('handouts')
