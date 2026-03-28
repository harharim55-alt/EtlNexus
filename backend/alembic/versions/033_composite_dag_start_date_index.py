"""Add composite index on (dag_id, start_date DESC) for run history

Covers the dominant query pattern in DAG summary batch methods and
resource lookups that filter by dag_id and order by start_date.

Revision ID: 033_composite_dag_start_date
Revises: 032_add_dag_id_index
Create Date: 2026-03-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "033_composite_dag_start_date"
down_revision: str | None = "032_add_dag_id_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_run_history_dag_start_date",
        "pipeline_run_history",
        ["dag_id", sa.text("start_date DESC NULLS LAST")],
    )


def downgrade() -> None:
    op.drop_index("ix_run_history_dag_start_date", "pipeline_run_history")
