"""Add visibility_grants table for team-scoped pipeline access control.

Each row grants a team access either to a specific pipeline or to all pipelines
owned by a source team. Exactly one of pipeline_id / source_team_id must be set,
enforced by a CHECK constraint.

Revision ID: 017_add_visibility_grants
Revises: 016_add_team_to_pipelines
Create Date: 2026-03-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "017_add_visibility_grants"
down_revision: Union[str, None] = "016_add_team_to_pipelines"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visibility_grants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("grantee_team_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=True),
        sa.Column("source_team_id", sa.Uuid(), nullable=True),
        sa.Column("granted_by", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["grantee_team_id"],
            ["teams.id"],
            name="fk_visibility_grants_grantee_team",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["pipeline_id"],
            ["pipelines.id"],
            name="fk_visibility_grants_pipeline",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_team_id"],
            ["teams.id"],
            name="fk_visibility_grants_source_team",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "(pipeline_id IS NOT NULL AND source_team_id IS NULL) OR "
            "(pipeline_id IS NULL AND source_team_id IS NOT NULL)",
            name="ck_visibility_grant_target",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_visibility_grants_grantee_team_id", "visibility_grants", ["grantee_team_id"])


def downgrade() -> None:
    op.drop_index("ix_visibility_grants_grantee_team_id", table_name="visibility_grants")
    op.drop_table("visibility_grants")
