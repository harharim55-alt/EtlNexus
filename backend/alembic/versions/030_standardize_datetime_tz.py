"""Standardize remaining naive DateTime columns to TIMESTAMPTZ.

Converts 8 columns that still use TIMESTAMP (without timezone) to
TIMESTAMP WITH TIME ZONE so that Python's timezone-aware datetime values
produced by datetime.now(timezone.utc) and func.now() are stored and
compared correctly by asyncpg without DataError.

Affected tables / columns:
  pipelines            — created_at, updated_at
  pipeline_run_history — recorded_at
  bouncers             — created_at, updated_at
  dag_tasks            — synced_at
  lineage_edges        — discovered_at
  pipeline_usages      — created_at

Revision ID: 030_standardize_datetime_tz
Revises: 029_rename_sensors_to_bouncers
Create Date: 2026-03-26
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "030_standardize_datetime_tz"
down_revision: str | None = "029_rename_sensors_to_bouncers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pipelines
    op.alter_column(
        "pipelines",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "pipelines",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # pipeline_run_history
    op.alter_column(
        "pipeline_run_history",
        "recorded_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # bouncers
    op.alter_column(
        "bouncers",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "bouncers",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # dag_tasks
    op.alter_column(
        "dag_tasks",
        "synced_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # lineage_edges
    op.alter_column(
        "lineage_edges",
        "discovered_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # pipeline_usages
    op.alter_column(
        "pipeline_usages",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )


def downgrade() -> None:
    # Reverse in opposite order to upgrade

    # pipeline_usages
    op.alter_column(
        "pipeline_usages",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # lineage_edges
    op.alter_column(
        "lineage_edges",
        "discovered_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # dag_tasks
    op.alter_column(
        "dag_tasks",
        "synced_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # bouncers
    op.alter_column(
        "bouncers",
        "updated_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "bouncers",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # pipeline_run_history
    op.alter_column(
        "pipeline_run_history",
        "recorded_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )

    # pipelines
    op.alter_column(
        "pipelines",
        "updated_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "pipelines",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
