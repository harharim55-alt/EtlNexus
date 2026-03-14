"""Add team (display name) and team_id (FK) columns to pipelines for ownership tracking.

Revision ID: 016_add_team_to_pipelines
Revises: 015_add_users_teams
Create Date: 2026-03-11
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "016_add_team_to_pipelines"
down_revision: str | None = "015_add_users_teams"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("team", sa.String(100), nullable=True),
    )
    op.add_column(
        "pipelines",
        sa.Column(
            "team_id",
            sa.Uuid(),
            sa.ForeignKey("teams.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_pipelines_team", "pipelines", ["team"])
    op.create_index("ix_pipelines_team_id", "pipelines", ["team_id"])


def downgrade() -> None:
    op.drop_index("ix_pipelines_team_id", table_name="pipelines")
    op.drop_index("ix_pipelines_team", table_name="pipelines")
    op.drop_column("pipelines", "team_id")
    op.drop_column("pipelines", "team")
