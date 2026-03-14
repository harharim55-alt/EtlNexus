"""Replace pipeline_id FK with etl_name in pipeline_usages

Revision ID: 005_usage_etl_name
Revises: 004_drop_code_path
Create Date: 2026-03-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005_usage_etl_name"
down_revision: str | None = "004_drop_code_path"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("pipeline_usages", sa.Column("etl_name", sa.String(255), nullable=True))
    # Populate etl_name from joined pipelines table
    op.execute(
        """
        UPDATE pipeline_usages SET etl_name = (
            SELECT LOWER(REPLACE(REPLACE(p.name, ' ', '_'), '-', '_'))
            FROM pipelines p WHERE p.id = pipeline_usages.pipeline_id
        )
        """
    )
    op.alter_column("pipeline_usages", "etl_name", nullable=False)
    op.drop_constraint("pipeline_usages_pipeline_id_fkey", "pipeline_usages", type_="foreignkey")
    op.drop_index("ix_pipeline_usages_pipeline_id", "pipeline_usages")
    op.drop_column("pipeline_usages", "pipeline_id")
    op.create_index("ix_pipeline_usages_etl_name", "pipeline_usages", ["etl_name"])


def downgrade() -> None:
    op.drop_index("ix_pipeline_usages_etl_name", "pipeline_usages")
    op.add_column("pipeline_usages", sa.Column("pipeline_id", sa.Uuid(), nullable=True))
    op.create_index("ix_pipeline_usages_pipeline_id", "pipeline_usages", ["pipeline_id"])
    op.create_foreign_key(
        "pipeline_usages_pipeline_id_fkey",
        "pipeline_usages",
        "pipelines",
        ["pipeline_id"],
        ["id"],
        ondelete="CASCADE",
    )
