"""Seed example data products on a fresh database.

Idempotent: only seeds when no products exist yet. Each product's ``task_id`` is
set to its name, which matches a seeded Iceberg table, so the catalog mirror
auto-fills the product's schema and the consume snippet renders. Products are
created the same way the New Data Product button creates them.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select

from app.config import configured_team_names, team_is_allowed
from app.database import async_session_factory
from app.models.pipeline import Pipeline
from app.repositories.team_repo import TeamRepository

logger = logging.getLogger(__name__)


async def seed_teams() -> None:
    """Pre-create the teams named in SYSTEM_TEAMS so they appear before any login.

    No-op when SYSTEM_TEAMS is the ``["*"]`` wildcard — there teams are created
    on demand from Keycloak groups at login instead.
    """
    names = configured_team_names()
    if not names:
        return
    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.get_or_create_many(names, source="config")
        await session.commit()
        logger.info("Ensured %d configured teams exist: %s", len(names), ", ".join(names))

# (team, name == Iceberg table name, schedule_type, description)
_SEED_PRODUCTS = [
    ("Dagger", "PortScanCollector", "hourly", "Raw port-scan observations across the monitored fleet."),
    ("Dagger", "BandwidthAnalyzer", "hourly", "Per-interface bandwidth utilisation analysis."),
    ("Dagger", "NetworkThreatAssessment", "daily", "Curated daily network threat assessment rollup."),
    ("Oasis", "DnsIntelSync", "hourly", "Synced DNS intelligence enrichment records."),
    ("Oasis", "IncidentForensicsRollup", "daily", "Daily incident forensics correlation rollup."),
    ("Prism", "ProtocolAnalyzer", "hourly", "Protocol-level traffic breakdown."),
    ("Prism", "TrafficClassifier", "hourly", "Classified traffic flows by application."),
    ("Vault", "AccessLogCollector", "hourly", "Collected access-log events."),
    ("Vault", "ThreatHunterScorer", "daily", "Threat-hunt risk scores per entity."),
    ("Vault", "WeeklyThreatDigest", "daily", "Published weekly threat digest."),
]


async def seed_data_products() -> None:
    """Insert example data products if the catalog is empty."""
    async with async_session_factory() as session:
        existing = await session.scalar(select(func.count()).select_from(Pipeline))
        if existing:
            logger.info("Data products already present (%d) — skipping seed", existing)
            return

        team_repo = TeamRepository(session)
        now = datetime.now(UTC)
        created = 0
        for team_name, name, schedule_type, description in _SEED_PRODUCTS:
            if not team_is_allowed(team_name):
                continue  # team excluded by SYSTEM_TEAMS allow-list
            team = await team_repo.get_or_create(team_name, source="seed")
            session.add(
                Pipeline(
                    name=name,
                    task_id=name,
                    description=description,
                    documentation=f"# {name}\n\n{description}\n\nSchema is fetched automatically from Spark Connect.",
                    team=team.name,
                    team_id=team.id,
                    schedule_type=schedule_type,
                    is_data_product=True,
                    last_updated_by="seed",
                    last_updated_at=now,
                )
            )
            created += 1

        await session.commit()
        logger.info("Seeded %d example data products", created)
