"""align manually added columns

Колонки characters.size, characters.effects и users.is_gm когда-то добавлялись в
работающую базу вручную (`ALTER TABLE ... ADD COLUMN ... DEFAULT ...`), потому что
create_all не умеет доливать колонки в существующие таблицы. Из-за этого в старой базе
у них остался серверный DEFAULT, а при установке с нуля его нет — схемы разъезжались.

Эта миграция снимает лишние серверные DEFAULT, приводя старую базу к тому же виду,
что и свежая. Значения по умолчанию задаёт сама модель (Python-side default в models.py),
поэтому на работу приложения это не влияет. На чистой базе миграция ничего не меняет:
DROP DEFAULT у колонки без DEFAULT в PostgreSQL — безопасная пустая операция.

Revision ID: 3c91d0a7e512
Revises: 2b844b3666f7
Create Date: 2026-07-22 18:40:00.000000
"""
from typing import Sequence, Union

from alembic import op


revision: str = '3c91d0a7e512'
down_revision: Union[str, None] = '2b844b3666f7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('characters', 'size', server_default=None)
    op.alter_column('characters', 'effects', server_default=None)
    op.alter_column('users', 'is_gm', server_default=None)


def downgrade() -> None:
    op.alter_column('characters', 'size', server_default='1.0')
    op.alter_column('characters', 'effects', server_default="'[]'::json")
    op.alter_column('users', 'is_gm', server_default='false')
