"""Drop Airflow / lineage / connection subsystems for the data-products-only model.

Removes the tables and pipeline columns belonging to the deleted Airflow,
lineage/topology, DAG/bouncer, run-history, resource, network, usage and
pipeline-log subsystems. The app is now a Data Products catalog: a Pipeline row
keeps only its catalog/product fields.

Uses ``IF EXISTS`` so it is safe to run regardless of which earlier tables/columns
are present.

Revision ID: 043_drop_airflow_and_connections
Revises: 042_add_catalog_mirror
"""

from alembic import op

revision: str = "043_drop_airflow_and_connections"
down_revision: str | None = "042_add_catalog_mirror"
branch_labels = None
depends_on = None

# Child tables first (FKs), then parents.
_DROP_TABLES = [
    "pipeline_log_networks",
    "pipeline_log_fields",
    "pipeline_logs",
    "pipeline_usages",
    "pipeline_run_history",
    "pipeline_resource_configs",
    "dag_tasks",
    "bouncers",
    "lineage_edges",
    "airflow_run_statuses",
    "networks",
]

_DROP_COLUMNS = [
    "category",
    "schedule",
    "rows_per_day",
    "how_to_read",
    "topology_enabled",
    "writes_to_manual",
    "reads_from_manual",
    "feeds_into_manual",
]


def upgrade() -> None:
    for table in _DROP_TABLES:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    for column in _DROP_COLUMNS:
        op.execute(f"ALTER TABLE pipelines DROP COLUMN IF EXISTS {column}")


def downgrade() -> None:
    # One-way migration: the dropped subsystems are not recreated. Restore from
    # an earlier revision/backup if needed.
    raise NotImplementedError("Downgrade not supported for the data-products-only collapse")
