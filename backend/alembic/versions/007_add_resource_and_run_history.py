"""Add pipeline_resource_configs and pipeline_run_history tables

Revision ID: 007_add_resource_run_history
Revises: 006_add_task_id
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007_add_resource_run_history"
down_revision: str | None = "006_add_task_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_resource_configs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("dag_id", sa.String(255), nullable=False),
        sa.Column("spark_driver_memory", sa.String(20), nullable=True),
        sa.Column("spark_executor_memory", sa.String(20), nullable=True),
        sa.Column("spark_executor_cores", sa.Integer(), nullable=True),
        sa.Column("spark_num_executors", sa.Integer(), nullable=True),
        sa.Column("is_dag_override", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("synced_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id", "dag_id", name="uq_resource_config_pipeline_dag"),
    )
    op.create_index(
        "ix_pipeline_resource_configs_pipeline_id",
        "pipeline_resource_configs",
        ["pipeline_id"],
    )

    op.create_table(
        "pipeline_run_history",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("dag_id", sa.String(255), nullable=False),
        sa.Column("dag_run_id", sa.String(255), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=True),
        sa.Column("start_date", sa.DateTime(), nullable=True),
        sa.Column("end_date", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("driver_memory_used_mb", sa.Integer(), nullable=True),
        sa.Column("executor_memory_peak_mb", sa.Integer(), nullable=True),
        sa.Column("cpu_utilization_pct", sa.Float(), nullable=True),
        sa.Column("executors_active", sa.Integer(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id", "dag_id", "dag_run_id", name="uq_run_history_pipeline_dag_run"),
    )
    op.create_index(
        "ix_pipeline_run_history_pipeline_id",
        "pipeline_run_history",
        ["pipeline_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_pipeline_run_history_pipeline_id", "pipeline_run_history")
    op.drop_table("pipeline_run_history")
    op.drop_index("ix_pipeline_resource_configs_pipeline_id", "pipeline_resource_configs")
    op.drop_table("pipeline_resource_configs")
