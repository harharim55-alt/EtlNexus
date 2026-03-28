"""Add failure_reason column to pipeline_run_history

Stores extracted failure root cause (OOM, timeout, connection refused, etc.)
parsed from Airflow task logs for failed runs.

Revision ID: 034_add_failure_reason
Revises: 033_composite_dag_start_date
Create Date: 2026-03-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "034_add_failure_reason"
down_revision: str | None = "033_composite_dag_start_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_history",
        sa.Column("failure_reason", sa.String(500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run_history", "failure_reason")
