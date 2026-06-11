"""Drop the visibility_grants table.

Visibility grants no longer affect anything (all products are viewable by every
user; editing is owning-team-only), so the table and feature are removed.

Revision ID: 045_drop_visibility_grants
Revises: 044_drop_beta_and_feature_flags
"""

from alembic import op

revision: str = "045_drop_visibility_grants"
down_revision: str | None = "044_drop_beta_and_feature_flags"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP TABLE IF EXISTS visibility_grants CASCADE")


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported — visibility grants were removed")
