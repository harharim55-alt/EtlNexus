"""Add user-level visibility grants.

Makes grantee_team_id nullable and adds grantee_user_id so grants can target
either a team or an individual user. Updates the CHECK constraint accordingly.

Revision ID: 018_add_user_visibility_grants
Revises: 017_add_visibility_grants
Create Date: 2026-03-11
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "018_add_user_visibility_grants"
down_revision: Union[str, None] = "017_add_visibility_grants"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add grantee_user_id column
    op.add_column(
        "visibility_grants",
        sa.Column("grantee_user_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_visibility_grants_grantee_user",
        "visibility_grants",
        "users",
        ["grantee_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_visibility_grants_grantee_user_id",
        "visibility_grants",
        ["grantee_user_id"],
    )

    # Make grantee_team_id nullable
    op.alter_column(
        "visibility_grants",
        "grantee_team_id",
        existing_type=sa.Uuid(),
        nullable=True,
    )

    # Drop old CHECK, add new one requiring exactly one grantee
    op.drop_constraint("ck_visibility_grant_target", "visibility_grants")
    op.create_check_constraint(
        "ck_visibility_grant_target",
        "visibility_grants",
        "(pipeline_id IS NOT NULL AND source_team_id IS NULL) OR "
        "(pipeline_id IS NULL AND source_team_id IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_visibility_grant_grantee",
        "visibility_grants",
        "(grantee_team_id IS NOT NULL AND grantee_user_id IS NULL) OR "
        "(grantee_team_id IS NULL AND grantee_user_id IS NOT NULL)",
    )


def downgrade() -> None:
    # Remove user grants first
    op.execute(
        "DELETE FROM visibility_grants WHERE grantee_user_id IS NOT NULL"
    )

    op.drop_constraint("ck_visibility_grant_grantee", "visibility_grants")
    op.drop_constraint("ck_visibility_grant_target", "visibility_grants")
    op.create_check_constraint(
        "ck_visibility_grant_target",
        "visibility_grants",
        "(pipeline_id IS NOT NULL AND source_team_id IS NULL) OR "
        "(pipeline_id IS NULL AND source_team_id IS NOT NULL)",
    )

    op.alter_column(
        "visibility_grants",
        "grantee_team_id",
        existing_type=sa.Uuid(),
        nullable=False,
    )

    op.drop_index("ix_visibility_grants_grantee_user_id", table_name="visibility_grants")
    op.drop_constraint("fk_visibility_grants_grantee_user", "visibility_grants", type_="foreignkey")
    op.drop_column("visibility_grants", "grantee_user_id")
