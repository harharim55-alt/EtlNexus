"""Add unique constraint on visibility_grants to prevent duplicates.

Uses a partial unique index approach since the columns are nullable (exactly
one of each pair is set, enforced by existing CHECK constraints).

Revision ID: 022_add_unique_grant_constraint
Revises: 021_add_vg_indexes
Create Date: 2026-03-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "022_add_unique_grant_constraint"
down_revision: str | None = "021_add_vg_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove exact duplicates first (keep the earliest created_at)
    op.execute("""
        DELETE FROM visibility_grants
        WHERE id NOT IN (
            SELECT DISTINCT ON (
                COALESCE(grantee_team_id::text, ''),
                COALESCE(grantee_user_id::text, ''),
                COALESCE(pipeline_id::text, ''),
                COALESCE(source_team_id::text, '')
            ) id
            FROM visibility_grants
            ORDER BY
                COALESCE(grantee_team_id::text, ''),
                COALESCE(grantee_user_id::text, ''),
                COALESCE(pipeline_id::text, ''),
                COALESCE(source_team_id::text, ''),
                created_at ASC
        )
    """)

    op.create_unique_constraint(
        "uq_visibility_grant_target_grantee",
        "visibility_grants",
        [
            "grantee_team_id",
            "grantee_user_id",
            "pipeline_id",
            "source_team_id",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_visibility_grant_target_grantee",
        "visibility_grants",
        type_="unique",
    )
