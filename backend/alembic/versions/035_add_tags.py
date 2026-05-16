"""Add tags and pipeline_tags tables

User-defined tags replace task groups for pipeline categorization.
Tags are owned by teams; pipelines can have multiple tags.

Revision ID: 035_add_tags
Revises: 034_add_failure_reason
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "035_add_tags"
down_revision: str | None = "034_add_failure_reason"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True, index=True),
        sa.Column("created_by_team_id", sa.Uuid(), sa.ForeignKey("teams.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "pipeline_tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pipeline_id", sa.Uuid(), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("tag_id", sa.Uuid(), sa.ForeignKey("tags.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.UniqueConstraint("pipeline_id", "tag_id", name="uq_pipeline_tag"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_tags")
    op.drop_table("tags")
