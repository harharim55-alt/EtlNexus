"""Add schema/lineage snapshot columns to pipeline_run_history.

Captures a point-in-time snapshot of the pipeline's schema (fields) and
lineage tables (source and destination) at the moment each run is recorded.
This allows historical analysis of how the pipeline's shape evolved over time
without joining against the current live state.

New columns (all nullable JSON):
  pipeline_run_history.fields_snapshot            — schema at run time
  pipeline_run_history.source_tables_snapshot     — source table names at run time
  pipeline_run_history.destination_tables_snapshot — dest table names at run time

Revision ID: 031_run_history_snapshots
Revises: 030_standardize_datetime_tz
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "031_run_history_snapshots"
down_revision: str | None = "030_standardize_datetime_tz"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "pipeline_run_history",
        sa.Column("fields_snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("source_tables_snapshot", sa.JSON(), nullable=True),
    )
    op.add_column(
        "pipeline_run_history",
        sa.Column("destination_tables_snapshot", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipeline_run_history", "destination_tables_snapshot")
    op.drop_column("pipeline_run_history", "source_tables_snapshot")
    op.drop_column("pipeline_run_history", "fields_snapshot")
