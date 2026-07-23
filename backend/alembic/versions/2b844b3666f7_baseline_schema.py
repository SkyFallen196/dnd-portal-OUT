"""baseline schema

Базовая ревизия: вся схема портала на момент подключения Alembic.

ВАЖНО: у уже работающей базы таблицы созданы раньше (через create_all), поэтому она
помечается этой ревизией командой `alembic stamp head` — миграция на ней не выполняется.
Чистая база получает те же таблицы через `alembic upgrade head`.

Порядок создания таблиц выставлен вручную: между rooms и maps круговая ссылка
(rooms.active_map_id -> maps.id, maps.room_id -> rooms.id), поэтому одна из связей
добавляется отдельным ALTER TABLE уже после создания обеих таблиц.

Revision ID: 2b844b3666f7
Revises:
Create Date: 2026-07-22 18:20:54.824110
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2b844b3666f7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('is_gm', sa.Boolean(), nullable=False),
        sa.Column('subscription_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    # rooms создаём БЕЗ связи на maps — её добавим ниже, когда maps появится.
    op.create_table(
        'rooms',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=120), nullable=False),
        sa.Column('gm_id', sa.Integer(), nullable=False),
        sa.Column('invite_code', sa.String(length=12), nullable=False),
        sa.Column('active_map_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gm_id'], ['users.id'], name='rooms_gm_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rooms_invite_code'), 'rooms', ['invite_code'], unique=True)

    op.create_table(
        'maps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(length=255), nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('width', sa.Integer(), nullable=False),
        sa.Column('height', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name='maps_room_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], name='maps_uploaded_by_fkey'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Замыкаем круг: теперь обе таблицы есть, можно связать rooms -> maps.
    op.create_foreign_key('rooms_active_map_id_fkey', 'rooms', 'maps', ['active_map_id'], ['id'])

    op.create_table(
        'access_codes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=32), nullable=False),
        sa.Column('created_by_admin_id', sa.Integer(), nullable=True),
        sa.Column('assigned_user_id', sa.Integer(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=False),
        sa.Column('is_activated', sa.Boolean(), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['assigned_user_id'], ['users.id'], name='access_codes_assigned_user_id_fkey'),
        sa.ForeignKeyConstraint(['created_by_admin_id'], ['users.id'], name='access_codes_created_by_admin_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_access_codes_code'), 'access_codes', ['code'], unique=True)

    op.create_table(
        'hero_sheets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('race', sa.String(length=60), nullable=False),
        sa.Column('age', sa.String(length=20), nullable=False),
        sa.Column('weight', sa.String(length=20), nullable=False),
        sa.Column('height', sa.String(length=20), nullable=False),
        sa.Column('portrait_url', sa.String(length=500), nullable=True),
        sa.Column('crop_position', sa.String(length=10), nullable=False),
        sa.Column('strength', sa.Integer(), nullable=False),
        sa.Column('dexterity', sa.Integer(), nullable=False),
        sa.Column('defense', sa.Integer(), nullable=False),
        sa.Column('hp', sa.Integer(), nullable=False),
        sa.Column('endurance', sa.Integer(), nullable=False),
        sa.Column('wisdom', sa.Integer(), nullable=False),
        sa.Column('intelligence', sa.Integer(), nullable=False),
        sa.Column('charisma', sa.Integer(), nullable=False),
        sa.Column('inventory', sa.JSON(), nullable=False),
        sa.Column('abilities', sa.JSON(), nullable=False),
        sa.Column('weaknesses', sa.JSON(), nullable=False),
        sa.Column('innate_ability', sa.String(length=200), nullable=False),
        sa.Column('backstory', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['owner_user_id'], ['users.id'], name='hero_sheets_owner_user_id_fkey', ondelete='CASCADE'
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_hero_sheets_owner_user_id'), 'hero_sheets', ['owner_user_id'], unique=False)

    op.create_table(
        'room_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name='room_members_room_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='room_members_user_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'characters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('owner_user_id', sa.Integer(), nullable=True),
        sa.Column('hero_sheet_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=80), nullable=False),
        sa.Column('color', sa.String(length=20), nullable=False),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('x', sa.Float(), nullable=False),
        sa.Column('y', sa.Float(), nullable=False),
        sa.Column('hp', sa.Integer(), nullable=False),
        sa.Column('max_hp', sa.Integer(), nullable=False),
        sa.Column('is_npc', sa.Boolean(), nullable=False),
        sa.Column('size', sa.Float(), nullable=False),
        sa.Column('effects', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['hero_sheet_id'], ['hero_sheets.id'], name='characters_hero_sheet_id_fkey', ondelete='SET NULL'
        ),
        sa.ForeignKeyConstraint(['owner_user_id'], ['users.id'], name='characters_owner_user_id_fkey'),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name='characters_room_id_fkey', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    op.create_table(
        'dice_rolls',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('room_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('formula', sa.String(length=100), nullable=False),
        sa.Column('rolls_json', sa.Text(), nullable=False),
        sa.Column('modifier', sa.Integer(), nullable=False),
        sa.Column('total', sa.Integer(), nullable=False),
        sa.Column('roll_type', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['room_id'], ['rooms.id'], name='dice_rolls_room_id_fkey', ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name='dice_rolls_user_id_fkey'),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('dice_rolls')
    op.drop_table('characters')
    op.drop_table('room_members')
    op.drop_index(op.f('ix_hero_sheets_owner_user_id'), table_name='hero_sheets')
    op.drop_table('hero_sheets')
    op.drop_index(op.f('ix_access_codes_code'), table_name='access_codes')
    op.drop_table('access_codes')
    # Сначала разрываем круг rooms -> maps, иначе таблицы не удалить.
    op.drop_constraint('rooms_active_map_id_fkey', 'rooms', type_='foreignkey')
    op.drop_table('maps')
    op.drop_index(op.f('ix_rooms_invite_code'), table_name='rooms')
    op.drop_table('rooms')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
