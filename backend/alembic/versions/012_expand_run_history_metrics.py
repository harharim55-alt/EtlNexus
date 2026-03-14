"""Expand pipeline_run_history with sparkMeasure metric columns.

Revision ID: 012_expand_run_history_metrics
Revises: 011_add_sensors
Create Date: 2026-03-10
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "012_expand_run_history_metrics"
down_revision: str | None = "011_add_sensors"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_history",
        sa.Column("spark_application_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("executor_run_time_ms", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("executor_cpu_time_ms", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("jvm_gc_time_ms", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("shuffle_read_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("shuffle_write_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("input_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("output_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("memory_bytes_spilled", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("disk_bytes_spilled", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("peak_execution_memory", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("result_size_bytes", sa.BigInteger(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("num_tasks", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("num_stages", sa.Integer(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("metrics_source", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run_history", "metrics_source")
    op.drop_column("pipeline_run_history", "num_stages")
    op.drop_column("pipeline_run_history", "num_tasks")
    op.drop_column("pipeline_run_history", "result_size_bytes")
    op.drop_column("pipeline_run_history", "peak_execution_memory")
    op.drop_column("pipeline_run_history", "disk_bytes_spilled")
    op.drop_column("pipeline_run_history", "memory_bytes_spilled")
    op.drop_column("pipeline_run_history", "output_bytes")
    op.drop_column("pipeline_run_history", "input_bytes")
    op.drop_column("pipeline_run_history", "shuffle_write_bytes")
    op.drop_column("pipeline_run_history", "shuffle_read_bytes")
    op.drop_column("pipeline_run_history", "jvm_gc_time_ms")
    op.drop_column("pipeline_run_history", "executor_cpu_time_ms")
    op.drop_column("pipeline_run_history", "executor_run_time_ms")
    op.drop_column("pipeline_run_history", "spark_application_id")
