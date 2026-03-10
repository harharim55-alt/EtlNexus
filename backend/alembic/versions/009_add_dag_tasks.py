"""Add dag_tasks table for caching Airflow DAG membership and task graph.

Revision ID: 009_add_dag_tasks
Revises: 008_run_history_composite_idx
Create Date: 2026-03-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009_add_dag_tasks"
down_revision: Union[str, None] = "008_run_history_composite_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "dag_tasks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("dag_id", sa.String(255), nullable=False, index=True),
        sa.Column("task_id", sa.String(255), nullable=False, index=True),
        sa.Column(
            "pipeline_id",
            sa.Uuid(),
            sa.ForeignKey("pipelines.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("downstream_task_ids", sa.JSON(), server_default="[]"),
        sa.Column("needs", sa.JSON(), server_default="[]"),
        sa.Column("prefers", sa.JSON(), server_default="[]"),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.now()),
        sa.UniqueConstraint("dag_id", "task_id", name="uq_dag_task"),
    )


def downgrade() -> None:
    op.drop_table("dag_tasks")
