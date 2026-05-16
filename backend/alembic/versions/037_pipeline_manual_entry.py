"""Add manual entry columns to pipelines

Supports manual data product management: how_to_read, import_snippet,
schedule_type, schema_manually_edited, topology_enabled, is_data_product,
writes_to_manual.

Revision ID: 037_pipeline_manual_entry
Revises: 036_add_networks
Create Date: 2026-04-06
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "037_pipeline_manual_entry"
down_revision: str | None = "036_add_networks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("how_to_read", sa.Text(), nullable=True))
    op.add_column("pipelines", sa.Column("import_snippet", sa.Text(), nullable=True))
    op.add_column("pipelines", sa.Column("schedule_type", sa.String(20), nullable=True))
    op.add_column(
        "pipelines",
        sa.Column("schema_manually_edited", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column("topology_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column("is_data_product", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column("pipelines", sa.Column("writes_to_manual", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipelines", "writes_to_manual")
    op.drop_column("pipelines", "is_data_product")
    op.drop_column("pipelines", "topology_enabled")
    op.drop_column("pipelines", "schema_manually_edited")
    op.drop_column("pipelines", "schedule_type")
    op.drop_column("pipelines", "import_snippet")
    op.drop_column("pipelines", "how_to_read")
