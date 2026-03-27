"""Add index on pipeline_run_history.dag_id

Speeds up lookups and joins by dag_id on the run history table.

Revision ID: 032_add_dag_id_index
Revises: 031_run_history_snapshots
Create Date: 2026-03-27
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "032_add_dag_id_index"
down_revision: str | None = "031_run_history_snapshots"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_pipeline_run_history_dag_id",
        "pipeline_run_history",
        ["dag_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_history_dag_id", "pipeline_run_history")
