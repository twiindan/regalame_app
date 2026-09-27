"""add product and productlist tables

Revision ID: 9f1c7b2a4d3e
Revises: 2b292b3ec677
Create Date: 2026-09-27

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel  # noqa: F401  (kept for parity with existing migrations)


revision: str = "9f1c7b2a4d3e"
down_revision: Union[str, Sequence[str], None] = "2b292b3ec677"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asin", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("title_normalized", sa.String(), nullable=False),
        sa.Column("image_url", sa.String(), nullable=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("category_slug", sa.String(), nullable=False),
        sa.Column("price_numeric", sa.Float(), nullable=True),
        sa.Column("price_raw", sa.String(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_product_asin", "product", ["asin"], unique=True)
    op.create_index("ix_product_title_normalized", "product", ["title_normalized"])
    op.create_index("ix_product_category", "product", ["category"])
    op.create_index("ix_product_category_slug", "product", ["category_slug"])
    op.create_index("ix_product_price_numeric", "product", ["price_numeric"])
    op.create_index("ix_product_is_active", "product", ["is_active"])

    op.create_table(
        "productlist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("list_key", sa.String(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("product_id", "list_key", name="uq_productlist_product_list"),
    )
    op.create_index("ix_productlist_product_id", "productlist", ["product_id"])
    op.create_index("ix_productlist_list_key", "productlist", ["list_key"])


def downgrade() -> None:
    op.drop_index("ix_productlist_list_key", table_name="productlist")
    op.drop_index("ix_productlist_product_id", table_name="productlist")
    op.drop_table("productlist")
    op.drop_index("ix_product_is_active", table_name="product")
    op.drop_index("ix_product_price_numeric", table_name="product")
    op.drop_index("ix_product_category_slug", table_name="product")
    op.drop_index("ix_product_category", table_name="product")
    op.drop_index("ix_product_title_normalized", table_name="product")
    op.drop_index("ix_product_asin", table_name="product")
    op.drop_table("product")
