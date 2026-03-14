"""Add execution_plan column to pipeline_run_history.

Revision ID: 013_add_execution_plan
Revises: 012_expand_run_history_metrics
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013_add_execution_plan"
down_revision: str | None = "012_expand_run_history_metrics"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_history",
        sa.Column("execution_plan", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run_history", "execution_plan")
