"""Add task_group_id column to dag_tasks for Airflow task group support.

Revision ID: 010_add_task_group_id
Revises: 009_add_dag_tasks
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010_add_task_group_id"
down_revision: str | None = "009_add_dag_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "dag_tasks",
        sa.Column("task_group_id", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("dag_tasks", "task_group_id")
