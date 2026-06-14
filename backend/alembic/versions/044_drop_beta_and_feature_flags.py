"""Drop beta support: the feature_flags table and users.is_beta column.

Beta gating (per-user is_beta + per-flag beta_only) only ever guarded the
removed DAG/Bouncer dashboards, so the whole feature-flag subsystem and the
beta flag are removed.

Revision ID: 044_drop_beta_and_feature_flags
Revises: 043_drop_airflow_and_connections
"""

from alembic import op

revision: str = "044_drop_beta_and_feature_flags"
down_revision: str | None = "043_drop_airflow_and_connections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS feature_flags CASCADE")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS is_beta")


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported — beta support was removed")
