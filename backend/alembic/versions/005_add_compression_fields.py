"""Add compression fields to chats and messages

Revision ID: 005
Revises: 004
Create Date: 2025-12-11
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add compressed_history_summary to chats table
    op.add_column(
        "chats",
        sa.Column(
            "compressed_history_summary",
            sa.Text(),
            nullable=True,
        ),
    )

    # Add is_compressed to messages table
    op.add_column(
        "messages",
        sa.Column(
            "is_compressed",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "is_compressed")
    op.drop_column("chats", "compressed_history_summary")
