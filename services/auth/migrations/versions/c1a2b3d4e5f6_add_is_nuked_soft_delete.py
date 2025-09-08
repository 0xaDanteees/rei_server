"""add is_nuked for soft delete and adjust email uniqueness

Revision ID: c1a2b3d4e5f6
Revises: b85c9fb6a750
Create Date: 2025-09-07 20:46:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "b85c9fb6a750"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add is_nuked column with default False
    op.add_column("users", sa.Column("is_nuked", sa.Boolean(), nullable=False, server_default=sa.text("false")))

    # 2) Drop existing unique constraint on email if present
    # Postgres default name for unnamed unique on column is typically 'users_email_key'
    op.execute(sa.text("ALTER TABLE users DROP CONSTRAINT IF EXISTS users_email_key"))

    # 3) Drop previous functional unique index if it exists
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_email_lower"))
    op.execute(sa.text("DROP INDEX IF EXISTS idx_users_email_lower"))

    # 4) Create new partial unique functional index for non-nuked users
    op.create_index(
        "idx_users_email_lower_active",
        "users",
        [sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("NOT is_nuked"),
    )


def downgrade() -> None:
    # Recreate prior unique index (non-partial) if needed and unique constraint
    op.execute(sa.text("DROP INDEX IF EXISTS idx_users_email_lower_active"))

    # Restore old unique index name if it existed previously
    op.create_index(
        "idx_users_email_lower",
        "users",
        [sa.text("lower(email)")],
        unique=True,
    )

    # Restore unique constraint on email
    op.execute(sa.text("ALTER TABLE users ADD CONSTRAINT users_email_key UNIQUE (email)"))

    # Drop is_nuked column
    op.drop_column("users", "is_nuked")
