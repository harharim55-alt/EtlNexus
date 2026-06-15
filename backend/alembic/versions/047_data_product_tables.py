"""Data products reference tables; tags removed.

Create the data_product_tables link table (product -> catalog table by
namespace+table_name), drop the product_tags table, and drop pipelines.is_tag.

Revision ID: 047_data_product_tables
Revises: 046_tags_as_data_products
"""

import sqlalchemy as sa
from alembic import op

revision: str = "047_data_product_tables"
down_revision: str | None = "046_tags_as_data_products"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "data_product_tables",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("product_id", sa.Uuid(), sa.ForeignKey("pipelines.id", ondelete="CASCADE"), nullable=False),
        sa.Column("namespace", sa.String(length=255), nullable=False),
        sa.Column("table_name", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("product_id", "namespace", "table_name", name="uq_data_product_table"),
    )
    op.create_index("ix_data_product_tables_product_id", "data_product_tables", ["product_id"])
    op.create_index("ix_data_product_tables_namespace", "data_product_tables", ["namespace"])
    op.create_index("ix_data_product_tables_table_name", "data_product_tables", ["table_name"])

    op.execute("DROP TABLE IF EXISTS product_tags CASCADE")
    op.drop_column("pipelines", "is_tag")


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported — data products now reference tables")
