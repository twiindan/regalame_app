"""Add auth fields to User

Revision ID: cc7ffafafaa0
Revises: 670b96d3fbc7
Create Date: 2025-12-11 15:39:22.874902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel # Add this line


# revision identifiers, used by Alembic.
revision: str = 'cc7ffafafaa0'
down_revision: Union[str, Sequence[str], None] = '670b96d3fbc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Add hashed_password as nullable first
    op.add_column('user', sa.Column('hashed_password', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    
    # 2. Update existing data
    # Dummy hash for "password" (bcrypt)
    dummy_hash = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW" 
    op.execute(f"UPDATE user SET hashed_password = '{dummy_hash}' WHERE hashed_password IS NULL")
    
    # 3. Update emails that are null (using SQLite string concatenation)
    op.execute("UPDATE user SET email = 'user_' || id || '@example.com' WHERE email IS NULL")
    
    # 4. Apply batch alter to enforce constraints (required for SQLite)
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.alter_column('hashed_password', nullable=False)
        batch_op.alter_column('email', nullable=False)
        batch_op.create_index(batch_op.f('ix_user_email'), ['email'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_email'))
        batch_op.alter_column('email', nullable=True)
        batch_op.drop_column('hashed_password')