"""Add history compression settings to chats

Revision ID: 004
Revises: 003
Create Date: 2025-12-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
  op.add_column(
      "chats",
      sa.Column(
          "history_compression_enabled",
          sa.Boolean(),
          nullable=False,
          server_default="false",
      ),
  )
  op.add_column(
      "chats",
      sa.Column(
          "history_compression_message_limit",
          sa.Integer(),
          nullable=True,
          server_default="10",
      ),
  )


def downgrade() -> None:
  op.drop_column("chats", "history_compression_message_limit")
  op.drop_column("chats", "history_compression_enabled")

