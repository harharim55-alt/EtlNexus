"""Add composite index on pipeline_run_history (pipeline_id, start_date DESC)

Revision ID: 008_run_history_composite_idx
Revises: 007_add_resource_run_history
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "008_run_history_composite_idx"
down_revision: str | None = "007_add_resource_run_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_run_history_pipeline_start_date",
        "pipeline_run_history",
        ["pipeline_id", sa.text("start_date DESC NULLS LAST")],
    )


def downgrade() -> None:
    op.drop_index("ix_run_history_pipeline_start_date", "pipeline_run_history")
