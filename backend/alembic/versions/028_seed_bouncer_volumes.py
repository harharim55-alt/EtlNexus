"""Seed bouncer volume_per_day values in the sensors table.

Revision ID: 028_seed_bouncer_volumes
Revises: 027_add_pipeline_revisions
Create Date: 2026-03-13
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "028_seed_bouncer_volumes"
down_revision: str | None = "027_add_pipeline_revisions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Bouncer volume data (previously hardcoded in DAG op_kwargs)
BOUNCER_VOLUMES = {
    "SwitchTelemetryBouncer": 2_400_000,
    "BgpFeedBouncer": 850_000,
    "NetflowCollectorBouncer": 5_200_000,
    "DnsQueryLogBouncer": 12_000_000,
    "SnmpTrapBouncer": 420_000,
    "SyslogReceiverBouncer": 8_500_000,
    "FirewallEventBouncer": 3_100_000,
    "HttpAccessLogBouncer": 18_000_000,
}


def upgrade() -> None:
    # Update existing rows (from old *Sensor names) and insert new ones
    sensors = sa.table(
        "sensors",
        sa.column("sensor_name", sa.String),
        sa.column("volume_per_day", sa.BigInteger),
    )
    for name, volume in BOUNCER_VOLUMES.items():
        op.execute(
            sensors.update()
            .where(sensors.c.sensor_name == name)
            .values(volume_per_day=volume)
        )


def downgrade() -> None:
    # No destructive downgrade — volume data is informational
    pass
