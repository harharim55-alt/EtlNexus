"""Add sensors table and sensor columns to dag_tasks.

Revision ID: 011_add_sensors
Revises: 010_add_task_group_id
Create Date: 2026-03-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011_add_sensors"
down_revision: Union[str, None] = "010_add_task_group_id"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sensors",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("sensor_name", sa.String(255), nullable=False, unique=True, index=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("team", sa.String(100), nullable=True, index=True),
        sa.Column("volume_per_day", sa.BigInteger(), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("dag_ids", sa.JSON(), server_default="[]"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )

    op.add_column(
        "dag_tasks",
        sa.Column("sensor_name", sa.String(255), nullable=True),
    )
    op.add_column(
        "dag_tasks",
        sa.Column(
            "sensor_id",
            sa.Uuid(),
            sa.ForeignKey("sensors.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("dag_tasks", "sensor_id")
    op.drop_column("dag_tasks", "sensor_name")
    op.drop_table("sensors")
