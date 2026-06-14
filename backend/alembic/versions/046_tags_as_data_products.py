"""Tags become data products.

Add pipelines.is_tag, create the product_tags link table (product->tag, both
pipelines), and drop the old lightweight tags / pipeline_tags tables.

Revision ID: 046_tags_as_data_products
Revises: 045_drop_visibility_grants
"""

import sqlalchemy as sa
from alembic import op

revision: str = "046_tags_as_data_products"
down_revision: str | None = "045_drop_visibility_grants"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("is_tag", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.create_table(
        "product_tags",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tag_id", sa.Uuid(), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.UniqueConstraint("product_id", "tag_id", name="uq_product_tag"),
    )
    op.create_index("ix_product_tags_product_id", "product_tags", ["product_id"])
    op.create_index("ix_product_tags_tag_id", "product_tags", ["tag_id"])
    op.execute("DROP TABLE IF EXISTS pipeline_tags CASCADE")
    op.execute("DROP TABLE IF EXISTS tags CASCADE")


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported — tags are now data products")
