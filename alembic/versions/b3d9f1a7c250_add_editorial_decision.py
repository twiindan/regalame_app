"""add editorial decision and gate state tables

Revision ID: b3d9f1a7c250
Revises: 9f1c7b2a4d3e
Create Date: 2026-10-04

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (kept for parity with existing migrations)


revision: str = "b3d9f1a7c250"
down_revision: Union[str, Sequence[str], None] = "9f1c7b2a4d3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "editorial_decision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(), nullable=True),
        sa.Column("context", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("model_id", sa.String(), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=True),
        sa.Column("input_fingerprint", sa.String(), nullable=True),
        sa.Column("classified_at", sa.DateTime(), nullable=True),
        sa.Column("manual_state", sa.String(), nullable=True),
        sa.Column("manual_context", sa.String(), nullable=True),
        sa.Column("manual_reason", sa.String(), nullable=True),
        sa.Column("manual_updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_editorial_decision_product_id",
        "editorial_decision",
        ["product_id"],
        unique=True,
    )

    op.create_table(
        "editorial_gate_state",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("gate_passed", sa.Boolean(), nullable=False),
        sa.Column("coverage_ratio", sa.Float(), nullable=False),
        sa.Column("unknown_ratio", sa.Float(), nullable=False),
        sa.Column("overall_agreement", sa.Float(), nullable=True),
        sa.Column("excluded_leak_ratio", sa.Float(), nullable=True),
        sa.Column("policy_version", sa.String(), nullable=False),
        sa.Column("model_id", sa.String(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("editorial_gate_state")
    op.drop_index("ix_editorial_decision_product_id", table_name="editorial_decision")
    op.drop_table("editorial_decision")
