"""Add catalog_columns table (Spark Connect schema mirror)

Mirrors Iceberg table schemas read from Spark Connect on a short interval so
end-user requests read schema data from Postgres and never hit Spark Connect
live. One row per column of a table.

Revision ID: 042_add_catalog_mirror
Revises: 041_add_topology_manual_fields
Create Date: 2026-06-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "042_add_catalog_mirror"
down_revision: str | None = "041_add_topology_manual_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "catalog_columns",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("namespace", sa.String(255), nullable=False, index=True),
        sa.Column("table_name", sa.String(255), nullable=False, index=True),
        sa.Column("column_name", sa.String(255), nullable=False, index=True),
        sa.Column("data_type", sa.String(50), nullable=True),
        sa.Column("ordinal_position", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("namespace", "table_name", "column_name", name="uq_catalog_col"),
    )
    op.create_index(
        "ix_catalog_columns_ns_table", "catalog_columns", ["namespace", "table_name"]
    )


def downgrade() -> None:
    op.drop_index("ix_catalog_columns_ns_table", table_name="catalog_columns")
    op.drop_table("catalog_columns")
