"""Rename sensors table to bouncers and sensor columns to bouncer columns.

Revision ID: 029_rename_sensors_to_bouncers
Revises: 028_seed_bouncer_volumes
Create Date: 2026-03-13
"""

from collections.abc import Sequence

from alembic import op

revision: str = "029_rename_sensors_to_bouncers"
down_revision: str | None = "028_seed_bouncer_volumes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Rename the sensors table to bouncers
    op.rename_table("sensors", "bouncers")

    # 2. Rename sensor_name column in bouncers table to bouncer_name
    op.alter_column("bouncers", "sensor_name", new_column_name="bouncer_name")

    # 3. Rename sensor_name and sensor_id columns in dag_tasks table
    op.alter_column("dag_tasks", "sensor_name", new_column_name="bouncer_name")
    op.alter_column("dag_tasks", "sensor_id", new_column_name="bouncer_id")

    # 4. Rename FK constraint on dag_tasks.bouncer_id
    #    (PostgreSQL auto-renames FK when table is renamed, but the constraint
    #     name stays the same — drop and recreate to keep naming consistent)
    op.drop_constraint("dag_tasks_sensor_id_fkey", "dag_tasks", type_="foreignkey")
    op.create_foreign_key(
        "dag_tasks_bouncer_id_fkey",
        "dag_tasks",
        "bouncers",
        ["bouncer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # 5. Rename indexes
    #    bouncers table: unique index on sensor_name -> bouncer_name
    op.execute("ALTER INDEX IF EXISTS ix_sensors_sensor_name RENAME TO ix_bouncers_bouncer_name")
    op.execute("ALTER INDEX IF EXISTS ix_sensors_team RENAME TO ix_bouncers_team")
    #    dag_tasks table: index on sensor_id -> bouncer_id
    op.execute("ALTER INDEX IF EXISTS ix_dag_tasks_sensor_id RENAME TO ix_dag_tasks_bouncer_id")


def downgrade() -> None:
    # Reverse index renames
    op.execute("ALTER INDEX IF EXISTS ix_dag_tasks_bouncer_id RENAME TO ix_dag_tasks_sensor_id")
    op.execute("ALTER INDEX IF EXISTS ix_bouncers_team RENAME TO ix_sensors_team")
    op.execute("ALTER INDEX IF EXISTS ix_bouncers_bouncer_name RENAME TO ix_sensors_sensor_name")

    # Reverse FK constraint rename
    op.drop_constraint("dag_tasks_bouncer_id_fkey", "dag_tasks", type_="foreignkey")
    op.create_foreign_key(
        "dag_tasks_sensor_id_fkey",
        "dag_tasks",
        "bouncers",
        ["bouncer_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Reverse column renames in dag_tasks
    op.alter_column("dag_tasks", "bouncer_id", new_column_name="sensor_id")
    op.alter_column("dag_tasks", "bouncer_name", new_column_name="sensor_name")

    # Reverse column rename in bouncers
    op.alter_column("bouncers", "bouncer_name", new_column_name="sensor_name")

    # Reverse table rename
    op.rename_table("bouncers", "sensors")
