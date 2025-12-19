"""Rename reserved field

Revision ID: 290908583dd4
Revises: 78d92e5a664d
Create Date: 2025-12-11 16:47:42.148145

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel # Add this line


# revision identifiers, used by Alembic.
revision: str = '290908583dd4'
down_revision: Union[str, Sequence[str], None] = '78d92e5a664d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite friendly batch rename
    with op.batch_alter_table('wish', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reserved_by_id', sa.Integer(), nullable=True))
        # Provide explicit name for the new FK
        batch_op.create_foreign_key('fk_wish_reserved_by_id_user', 'user', ['reserved_by_id'], ['id'])
        # Drop old column (will auto-drop its unnamed FK in sqlite batch recreation)
        batch_op.drop_column('reserved_by_user_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('wish', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reserved_by_user_id', sa.INTEGER(), nullable=True))
        # Drop the named constraint we created
        batch_op.drop_constraint('fk_wish_reserved_by_id_user', type_='foreignkey')
        batch_op.drop_column('reserved_by_id')