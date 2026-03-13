"""Add GIN trigram indexes for ILIKE search performance.

Creates pg_trgm extension and GIN indexes on pipelines.name,
pipelines.description, and pipeline_fields.name to accelerate
ILIKE '%query%' patterns used by pipeline search.

Revision ID: 025_gin_trigram_indexes
Revises: 024_run_history_tz
Create Date: 2026-03-13
"""

from alembic import op

revision = "025_gin_trigram_indexes"
down_revision = "024_run_history_tz"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pipeline_name_trgm "
        "ON pipelines USING gin(name gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pipeline_desc_trgm "
        "ON pipelines USING gin(description gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_field_name_trgm "
        "ON pipeline_fields USING gin(name gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_field_name_trgm")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_desc_trgm")
    op.execute("DROP INDEX IF EXISTS idx_pipeline_name_trgm")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
