"""Make all remaining datetime columns timezone-aware.

Covers pipeline_run_history (start_date, end_date),
airflow_run_statuses (execution_date, last_checked_at),
pipeline_resource_configs (synced_at),
and pipeline_usages (last_accessed_at).

All these columns receive or are compared against timezone-aware
datetime.now(timezone.utc) values. The column type must match to
avoid asyncpg DataError.

Revision ID: 024_run_history_tz
Revises: 023_datetime_timezone
Create Date: 2026-03-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "024_run_history_tz"
down_revision: str | None = "023_datetime_timezone"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pipeline_run_history
    op.alter_column(
        "pipeline_run_history",
        "start_date",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "pipeline_run_history",
        "end_date",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    # airflow_run_statuses
    op.alter_column(
        "airflow_run_statuses",
        "execution_date",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "airflow_run_statuses",
        "last_checked_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    # pipeline_resource_configs
    op.alter_column(
        "pipeline_resource_configs",
        "synced_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
    )
    # pipeline_usages
    op.alter_column(
        "pipeline_usages",
        "last_accessed_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "pipeline_usages",
        "last_accessed_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "pipeline_resource_configs",
        "synced_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "airflow_run_statuses",
        "last_checked_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "airflow_run_statuses",
        "execution_date",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "pipeline_run_history",
        "end_date",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "pipeline_run_history",
        "start_date",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
