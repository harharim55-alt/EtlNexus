"""Make last_login and last_updated_at timezone-aware.

These columns receive Python-generated `datetime.now(timezone.utc)` values.
The column type must be TIMESTAMP WITH TIME ZONE to avoid offset-naive vs
offset-aware mismatch errors from asyncpg.

Revision ID: 023_datetime_timezone
Revises: 022_add_unique_grant_constraint
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023_datetime_timezone"
down_revision: Union[str, None] = "022_add_unique_grant_constraint"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "users",
        "last_login",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "pipelines",
        "last_updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "pipelines",
        "last_updated_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "users",
        "last_login",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
