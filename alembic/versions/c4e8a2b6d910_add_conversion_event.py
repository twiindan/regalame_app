"""add privacy-scoped conversion event table

Revision ID: c4e8a2b6d910
Revises: b3d9f1a7c250
Create Date: 2026-10-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (kept for parity with existing migrations)


revision: str = "c4e8a2b6d910"
down_revision: Union[str, Sequence[str], None] = "b3d9f1a7c250"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "conversion_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_conversion_event_name", "conversion_event", ["name"], unique=False)
    op.create_index(
        "ix_conversion_event_occurred_at", "conversion_event", ["occurred_at"], unique=False
    )
    op.create_index(
        "ix_conversion_event_name_occurred_at",
        "conversion_event",
        ["name", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_conversion_event_name_occurred_at", table_name="conversion_event")
    op.drop_index("ix_conversion_event_occurred_at", table_name="conversion_event")
    op.drop_index("ix_conversion_event_name", table_name="conversion_event")
    op.drop_table("conversion_event")
