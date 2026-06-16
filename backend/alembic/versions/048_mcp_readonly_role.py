"""Least-privilege read-only role + catalog-only views for the MCP server.

The AI Architect queries Postgres through an MCP server. That server connects as
``mcp_readonly`` — a login role that can read ONLY the views in the ``mcp`` schema
(catalog metadata, PII-excluded). It has no privileges on the base ``public``
tables, so ``users`` / ``user_teams`` and excluded columns are unreachable even
via arbitrary SELECT.

Revision ID: 048_mcp_readonly_role
Revises: 047_data_product_tables
"""

import os

from alembic import op

revision: str = "048_mcp_readonly_role"
down_revision: str | None = "047_data_product_tables"
branch_labels = None
depends_on = None

# Views expose only non-sensitive columns (no last_updated_by / task_id /
# import_snippet / changed_by; no users / user_teams at all).
_VIEWS = {
    "pipelines": "SELECT id, name, description, documentation, team, schedule_type, "
                 "is_data_product, created_at, updated_at FROM public.pipelines",
    "pipeline_fields": "SELECT id, pipeline_id, name, data_type, ordinal_position "
                       "FROM public.pipeline_fields",
    "catalog_columns": "SELECT id, namespace, table_name, column_name, data_type, "
                       "ordinal_position, synced_at FROM public.catalog_columns",
    "data_product_tables": "SELECT id, product_id, namespace, table_name "
                           "FROM public.data_product_tables",
    "teams": "SELECT id, name, description FROM public.teams",
    "pipeline_revisions": "SELECT id, pipeline_id, field_name, content, change_source, "
                          "created_at FROM public.pipeline_revisions",
}


def upgrade() -> None:
    password = os.getenv("MCP_DB_PASSWORD", "mcp_readonly_pw").replace("'", "''")

    # Idempotent role create/sync (roles are cluster-global).
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'mcp_readonly') THEN
                CREATE ROLE mcp_readonly LOGIN PASSWORD '{password}';
            ELSE
                ALTER ROLE mcp_readonly LOGIN PASSWORD '{password}';
            END IF;
        END
        $$;
        """
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS mcp;")
    for name, select_sql in _VIEWS.items():
        op.execute(f"CREATE OR REPLACE VIEW mcp.{name} AS {select_sql};")

    # Least privilege: only the mcp schema + its views, nothing in public.
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM mcp_readonly;")
    op.execute("GRANT USAGE ON SCHEMA mcp TO mcp_readonly;")
    op.execute("GRANT SELECT ON ALL TABLES IN SCHEMA mcp TO mcp_readonly;")
    op.execute("ALTER ROLE mcp_readonly SET search_path = mcp;")


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS mcp CASCADE;")
    op.execute("REVOKE ALL ON SCHEMA public FROM mcp_readonly;")
    op.execute("DROP ROLE IF EXISTS mcp_readonly;")
