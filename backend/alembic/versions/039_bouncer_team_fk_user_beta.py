"""Add bouncer team FK and user is_beta flag

Bouncers can now be manually assigned to teams. Users can be flagged
as beta testers for gated features.

Revision ID: 039_bouncer_team_user_beta
Revises: 038_add_pipeline_logs
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "039_bouncer_team_user_beta"
down_revision: str | None = "038_add_pipeline_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bouncers",
        sa.Column("team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True, index=True),
    )
    op.add_column(
        "users",
        sa.Column("is_beta", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "is_beta")
    op.drop_column("bouncers", "team_id")
