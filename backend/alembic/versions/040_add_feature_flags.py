"""Add feature_flags table

Controls access to beta features (DAG dashboard, Bouncer dashboard).
Flags can be globally enabled/disabled and optionally restricted to beta users.

Revision ID: 040_add_feature_flags
Revises: 039_bouncer_team_user_beta
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "040_add_feature_flags"
down_revision: str | None = "039_bouncer_team_user_beta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("beta_only", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
    )

    # Seed default feature flags
    op.execute(
        "INSERT INTO feature_flags (id, name, enabled, beta_only, description) VALUES "
        "(gen_random_uuid(), 'dag_dashboard', false, true, 'DAG operations dashboard'), "
        "(gen_random_uuid(), 'bouncer_dashboard', false, true, 'Bouncer monitoring dashboard')"
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
