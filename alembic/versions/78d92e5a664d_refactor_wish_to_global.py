"""Refactor Wish to Global

Revision ID: 78d92e5a664d
Revises: cc7ffafafaa0
Create Date: 2025-12-11 16:38:57.521625

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel # Add this line


# revision identifiers, used by Alembic.
revision: str = '78d92e5a664d'
down_revision: Union[str, Sequence[str], None] = 'cc7ffafafaa0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # SQLite batch mode handles dropping FKs by recreating the table.
    # We don't need to explicitly drop the unnamed constraint if we drop the column.
    with op.batch_alter_table('wish', schema=None) as batch_op:
        batch_op.add_column(sa.Column('reserved_by_user_id', sa.Integer(), nullable=True))
        # Remove the explicit drop_constraint call that fails on SQLite with unnamed FKs
        # batch_op.drop_constraint(None, type_='foreignkey') 
        batch_op.drop_column('group_id')


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('wish', schema=None) as batch_op:
        batch_op.add_column(sa.Column('group_id', sa.INTEGER(), nullable=True)) # Temporarily nullable for data migration
        # Re-add constraint with a name if possible, or let batch handle it
        batch_op.create_foreign_key('fk_wish_group_id', 'group', ['group_id'], ['id'])
        batch_op.drop_column('reserved_by_user_id')