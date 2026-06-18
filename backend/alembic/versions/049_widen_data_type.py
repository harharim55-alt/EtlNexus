"""Widen data_type columns to TEXT.

Real Spark/Iceberg column types (DECIMAL(38,18), ARRAY<...>, STRUCT<...>, MAP<...>)
easily exceed varchar(50), which made the catalog-mirror bulk insert fail and
roll back the whole refresh (catalog_columns stayed empty). Use TEXT.

Revision ID: 049_widen_data_type
Revises: 048_mcp_readonly_role
"""

import sqlalchemy as sa
from alembic import op

revision: str = "049_widen_data_type"
down_revision: str | None = "048_mcp_readonly_role"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The mcp.catalog_columns + mcp.pipeline_fields views (migration 048) depend on
    # data_type, which blocks ALTER TYPE — drop them, widen, recreate, re-grant.
    op.execute("DROP VIEW IF EXISTS mcp.catalog_columns")
    op.execute("DROP VIEW IF EXISTS mcp.pipeline_fields")

    op.alter_column("catalog_columns", "data_type",
                    type_=sa.Text(), existing_type=sa.String(length=50), existing_nullable=True)
    op.alter_column("pipeline_fields", "data_type",
                    type_=sa.Text(), existing_type=sa.String(length=50), existing_nullable=True)

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'mcp') THEN
                CREATE OR REPLACE VIEW mcp.catalog_columns AS
                    SELECT id, namespace, table_name, column_name, data_type, ordinal_position, synced_at
                    FROM public.catalog_columns;
                CREATE OR REPLACE VIEW mcp.pipeline_fields AS
                    SELECT id, pipeline_id, name, data_type, ordinal_position
                    FROM public.pipeline_fields;
                IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_readonly') THEN
                    GRANT SELECT ON mcp.catalog_columns TO mcp_readonly;
                    GRANT SELECT ON mcp.pipeline_fields TO mcp_readonly;
                END IF;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade not supported — data_type widened to TEXT")
