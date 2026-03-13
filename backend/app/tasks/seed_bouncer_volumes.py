"""Seed bouncer volume_per_day values after Airflow sync creates the rows."""

import logging

from sqlalchemy import select, update

from app.database import async_session_factory
from app.models.sensor import Bouncer

logger = logging.getLogger(__name__)

# Same volume data as migration 028
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


async def seed_bouncer_volumes() -> None:
    """Set volume_per_day for bouncers that have NULL values."""
    try:
        async with async_session_factory() as session:
            # Check if any bouncers are missing volume data
            stmt = select(Bouncer.sensor_name).where(
                Bouncer.sensor_name.in_(list(BOUNCER_VOLUMES.keys())),
                Bouncer.volume_per_day.is_(None),
            )
            result = await session.execute(stmt)
            missing = [row[0] for row in result.all()]

            if not missing:
                logger.info("All bouncer volumes already seeded, skipping")
                return

            for name in missing:
                await session.execute(
                    update(Bouncer)
                    .where(Bouncer.sensor_name == name)
                    .values(volume_per_day=BOUNCER_VOLUMES[name])
                )

            await session.commit()
            logger.info("Seeded volume_per_day for %d bouncers", len(missing))
    except Exception:
        logger.exception("Failed to seed bouncer volumes")
