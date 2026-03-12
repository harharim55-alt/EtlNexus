"""Add composite indexes on visibility_grants for list_visible performance.

The list_visible query runs 4 correlated subqueries on every non-admin
pipeline list request. These partial composite indexes cover each pattern
and keep the index small by filtering on NOT NULL.

Revision ID: 021_add_vg_indexes
Revises: 020_add_role_check_constraints
Create Date: 2026-03-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021_add_vg_indexes"
down_revision: Union[str, None] = "020_add_role_check_constraints"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_vg_team_pipeline",
        "visibility_grants",
        ["grantee_team_id", "pipeline_id"],
        postgresql_where=sa.text("pipeline_id IS NOT NULL"),
    )
    op.create_index(
        "ix_vg_team_source",
        "visibility_grants",
        ["grantee_team_id", "source_team_id"],
        postgresql_where=sa.text("source_team_id IS NOT NULL"),
    )
    op.create_index(
        "ix_vg_user_pipeline",
        "visibility_grants",
        ["grantee_user_id", "pipeline_id"],
        postgresql_where=sa.text("pipeline_id IS NOT NULL"),
    )
    op.create_index(
        "ix_vg_user_source",
        "visibility_grants",
        ["grantee_user_id", "source_team_id"],
        postgresql_where=sa.text("source_team_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_vg_user_source", table_name="visibility_grants")
    op.drop_index("ix_vg_user_pipeline", table_name="visibility_grants")
    op.drop_index("ix_vg_team_source", table_name="visibility_grants")
    op.drop_index("ix_vg_team_pipeline", table_name="visibility_grants")
