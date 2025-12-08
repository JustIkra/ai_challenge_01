"""Add temperature to chats

Revision ID: 003
Revises: 002
Create Date: 2025-12-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('chats', sa.Column('temperature', sa.Float(), nullable=True, server_default='0.7'))


def downgrade() -> None:
    op.drop_column('chats', 'temperature')
