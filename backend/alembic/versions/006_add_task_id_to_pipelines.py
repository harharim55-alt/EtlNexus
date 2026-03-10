"""Add task_id column to pipelines for lossless Airflow task ID storage

Revision ID: 006_add_task_id
Revises: 005_usage_etl_name
Create Date: 2026-03-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006_add_task_id"
down_revision: Union[str, None] = "005_usage_etl_name"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("task_id", sa.String(255), nullable=True))
    op.create_index("ix_pipelines_task_id", "pipelines", ["task_id"])
    # Backfill from existing names: "Shopify Sales Sync" -> "shopify_sales_sync"
    op.execute(
        """
        UPDATE pipelines SET task_id = LOWER(REPLACE(REPLACE(name, ' ', '_'), '-', '_'))
        """
    )


def downgrade() -> None:
    op.drop_index("ix_pipelines_task_id", "pipelines")
    op.drop_column("pipelines", "task_id")
