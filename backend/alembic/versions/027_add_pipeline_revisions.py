"""Add pipeline_revisions table and description_edited_by_user flag.

Revision ID: 027_add_pipeline_revisions
Revises: 026_tz_indexes_granted_by
Create Date: 2026-03-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "027_add_pipeline_revisions"
down_revision: str | None = "026_tz_indexes_granted_by"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_revisions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "pipeline_id",
            sa.UUID(),
            sa.ForeignKey("pipelines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(255), nullable=False),
        sa.Column("change_source", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_pipeline_revisions_pipeline_id",
        "pipeline_revisions",
        ["pipeline_id"],
    )
    op.create_index(
        "ix_pipeline_revisions_pipeline_field",
        "pipeline_revisions",
        ["pipeline_id", "field_name"],
    )

    op.add_column(
        "pipelines",
        sa.Column(
            "description_edited_by_user",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("pipelines", "description_edited_by_user")
    op.drop_index("ix_pipeline_revisions_pipeline_field", table_name="pipeline_revisions")
    op.drop_index("ix_pipeline_revisions_pipeline_id", table_name="pipeline_revisions")
    op.drop_table("pipeline_revisions")
