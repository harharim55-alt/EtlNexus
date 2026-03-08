"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2026-03-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipelines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("schedule", sa.String(100), nullable=True),
        sa.Column("rows_per_day", sa.String(50), nullable=True),
        sa.Column("code_path", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_pipelines_name", "pipelines", ["name"])

    op.create_table(
        "pipeline_fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("ordinal_position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_pipeline_fields_pipeline_id", "pipeline_fields", ["pipeline_id"])
    op.create_index("ix_pipeline_fields_name", "pipeline_fields", ["name"])

    op.create_table(
        "lineage_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_pipeline_id", sa.Uuid(), nullable=True),
        sa.Column("target_pipeline_id", sa.Uuid(), nullable=True),
        sa.Column("source_table", sa.String(500), nullable=False),
        sa.Column("target_table", sa.String(500), nullable=False),
        sa.Column("edge_type", sa.String(20), nullable=False),
        sa.Column("discovered_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_pipeline_id"], ["pipelines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_pipeline_id"], ["pipelines.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_lineage_edges_source_pipeline_id", "lineage_edges", ["source_pipeline_id"])
    op.create_index("ix_lineage_edges_target_pipeline_id", "lineage_edges", ["target_pipeline_id"])

    op.create_table(
        "airflow_run_statuses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("dag_id", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("execution_date", sa.DateTime(), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("pipeline_id"),
    )

    op.create_table(
        "dag_networks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_id", sa.Uuid(), nullable=False),
        sa.Column("network_name", sa.String(255), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dag_networks_pipeline_id", "dag_networks", ["pipeline_id"])


def downgrade() -> None:
    op.drop_table("dag_networks")
    op.drop_table("airflow_run_statuses")
    op.drop_table("lineage_edges")
    op.drop_table("pipeline_fields")
    op.drop_table("pipelines")
