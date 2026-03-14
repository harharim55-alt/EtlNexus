"""Add grant_level column to visibility_grants.

Revision ID: 019_add_grant_level
Revises: 018_add_user_visibility_grants
"""


import sqlalchemy as sa

from alembic import op

revision: str = "019_add_grant_level"
down_revision: str | None = "018_add_user_visibility_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "visibility_grants",
        sa.Column(
            "grant_level",
            sa.String(20),
            nullable=False,
            server_default="viewer",
        ),
    )


def downgrade() -> None:
    op.drop_column("visibility_grants", "grant_level")
