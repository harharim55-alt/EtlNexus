"""Add multi-log data structure tables

Each pipeline can have multiple named logs. Each log has its own schema
(fields) and is available on specific networks with per-network retention.

Revision ID: 038_add_pipeline_logs
Revises: 037_pipeline_manual_entry
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "038_add_pipeline_logs"
down_revision: str | None = "037_pipeline_manual_entry"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "pipeline_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("pipeline_id", sa.Uuid(), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("ordinal_position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        "pipeline_log_networks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("log_id", sa.Uuid(), sa.ForeignKey("pipeline_logs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("network_id", sa.Uuid(), sa.ForeignKey("networks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("retention", sa.String(100), nullable=True),
        sa.UniqueConstraint("log_id", "network_id", name="uq_log_network"),
    )

    op.create_table(
        "pipeline_log_fields",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("log_id", sa.Uuid(), sa.ForeignKey("pipeline_logs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("ordinal_position", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("pipeline_log_fields")
    op.drop_table("pipeline_log_networks")
    op.drop_table("pipeline_logs")
