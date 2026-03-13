"""Make remaining DateTime columns timezone-aware, add granted_by_user_id FK,
and add missing indexes on visibility_grants.pipeline_id / source_team_id.

Revision ID: 026_tz_indexes_granted_by
Revises: 025_gin_trigram_indexes
Create Date: 2026-03-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "026_tz_indexes_granted_by"
down_revision: Union[str, None] = "025_gin_trigram_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Columns to make timezone-aware: (table, column, nullable)
_TZ_COLUMNS = [
    ("teams", "created_at", False),
    ("users", "created_at", False),
    ("users", "updated_at", False),
    ("user_teams", "joined_at", False),
    ("visibility_grants", "created_at", False),
]


def upgrade() -> None:
    # --- Issue 11: timezone-aware DateTime columns ---
    for table, column, nullable in _TZ_COLUMNS:
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=nullable,
        )

    # --- Issue 12: granted_by_user_id audit column ---
    op.add_column(
        "visibility_grants",
        sa.Column("granted_by_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_vg_granted_by_user",
        "visibility_grants",
        "users",
        ["granted_by_user_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # --- Issue 18: missing single-column indexes ---
    op.create_index(
        "ix_visibility_grants_pipeline_id",
        "visibility_grants",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_visibility_grants_source_team_id",
        "visibility_grants",
        ["source_team_id"],
    )


def downgrade() -> None:
    # Reverse indexes
    op.drop_index("ix_visibility_grants_source_team_id", table_name="visibility_grants")
    op.drop_index("ix_visibility_grants_pipeline_id", table_name="visibility_grants")

    # Reverse granted_by_user_id
    op.drop_constraint("fk_vg_granted_by_user", "visibility_grants", type_="foreignkey")
    op.drop_column("visibility_grants", "granted_by_user_id")

    # Reverse timezone columns
    for table, column, nullable in reversed(_TZ_COLUMNS):
        op.alter_column(
            table,
            column,
            type_=sa.DateTime(),
            existing_type=sa.DateTime(timezone=True),
            existing_nullable=nullable,
        )
