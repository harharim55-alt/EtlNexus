"""Drop dag_networks table — networks now sourced from Airflow

Revision ID: 003_drop_dag_networks
Revises: 002_usages
Create Date: 2026-03-08
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003_drop_dag_networks"
down_revision: str | None = "002_usages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_dag_networks_pipeline_id", table_name="dag_networks")
    op.drop_table("dag_networks")


def downgrade() -> None:
    op.create_table(
        "dag_networks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("pipeline_id", sa.UUID(), nullable=False),
        sa.Column("network_name", sa.String(255), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["pipeline_id"], ["pipelines.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_dag_networks_pipeline_id", "dag_networks", ["pipeline_id"])
