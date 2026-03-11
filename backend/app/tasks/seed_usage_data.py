"""Seed pipeline_usages table with enrichment data for downstream consumers and self-read counts."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.pipeline_usage import PipelineUsage

logger = logging.getLogger(__name__)

# Enrichment data keyed by etl_name → list of entries.
# First entry per ETL is a self-entry (consumer_name = etl_name) for the ETL's own read count.
# Remaining entries are downstream consumers (consumer_name = Airflow downstream task_id).
SEED_USAGES: dict[str, list[dict]] = {
    "SwitchPortCollector": [
        {"consumer_name": "SwitchPortCollector", "usage_type": "etl", "description": None, "access_count": 18200, "days_ago": 0},
        {"consumer_name": "BgpRouteSync", "usage_type": "etl", "description": "Syncs BGP route tables using switch port interface data", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "DnsRecordSync", "usage_type": "etl", "description": "Enriches DNS zone sync with port-level network topology", "access_count": 4380, "days_ago": 0},
        {"consumer_name": "NetflowCapture", "usage_type": "etl", "description": "Maps NetFlow records to physical switch port interfaces", "access_count": 2100, "days_ago": 0},
    ],
    "BgpRouteSync": [
        {"consumer_name": "BgpRouteSync", "usage_type": "etl", "description": None, "access_count": 9450, "days_ago": 0},
        {"consumer_name": "BandwidthBillingAggregator", "usage_type": "etl", "description": "Aggregates bandwidth billing from BGP route announcements", "access_count": 1847, "days_ago": 0},
        {"consumer_name": "DeviceFingerprintEnrichment", "usage_type": "etl", "description": "Enriches device fingerprints with BGP routing context", "access_count": 4200, "days_ago": 0},
        {"consumer_name": "BandwidthCostReconciliation", "usage_type": "etl", "description": "Reconciles metered bandwidth against BGP route records", "access_count": 730, "days_ago": 0},
    ],
    "DnsRecordSync": [
        {"consumer_name": "DnsRecordSync", "usage_type": "etl", "description": None, "access_count": 5120, "days_ago": 0},
        {"consumer_name": "BandwidthBillingAggregator", "usage_type": "etl", "description": "Cross-references DNS zones with bandwidth billing data", "access_count": 1234, "days_ago": 0},
        {"consumer_name": "DeviceFingerprintEnrichment", "usage_type": "etl", "description": "Merges DNS resolution data into unified device profiles", "access_count": 1890, "days_ago": 0},
        {"consumer_name": "IncidentAnalyticsRollup", "usage_type": "etl", "description": "Correlates syslog incidents with DNS resolution context", "access_count": 445, "days_ago": 1},
    ],
    "NetflowCapture": [
        {"consumer_name": "NetflowCapture", "usage_type": "etl", "description": None, "access_count": 7630, "days_ago": 0},
        {"consumer_name": "LinkFailurePrediction", "usage_type": "etl", "description": "Flow-level traffic features for link failure prediction model", "access_count": 3420, "days_ago": 0},
    ],
    "SyslogEventStream": [
        {"consumer_name": "SyslogEventStream", "usage_type": "etl", "description": None, "access_count": 12400, "days_ago": 0},
        {"consumer_name": "IncidentAnalyticsRollup", "usage_type": "etl", "description": "Aggregates syslog event volume and severity metrics", "access_count": 2103, "days_ago": 0},
    ],
    "BandwidthBillingAggregator": [
        {"consumer_name": "BandwidthBillingAggregator", "usage_type": "etl", "description": None, "access_count": 3780, "days_ago": 0},
        {"consumer_name": "BandwidthCostReconciliation", "usage_type": "etl", "description": "Input to bandwidth variance and cost reconciliation analysis", "access_count": 956, "days_ago": 0},
        {"consumer_name": "BandwidthReportsApiDummy", "usage_type": "api", "description": "Feeds aggregated bandwidth data to reports API endpoint", "access_count": 365, "days_ago": 1},
    ],
    "DeviceFingerprintEnrichment": [
        {"consumer_name": "DeviceFingerprintEnrichment", "usage_type": "etl", "description": None, "access_count": 6890, "days_ago": 0},
        {"consumer_name": "LinkFailurePrediction", "usage_type": "etl", "description": "Device health signals for link failure feature pipeline", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "NetworkInsightsApiDummy", "usage_type": "api", "description": "Serves enriched device data via network insights API", "access_count": 3200, "days_ago": 0},
    ],
    "LinkFailurePrediction": [
        {"consumer_name": "LinkFailurePrediction", "usage_type": "etl", "description": None, "access_count": 8210, "days_ago": 0},
        {"consumer_name": "NocDashboardSnapshot", "usage_type": "etl", "description": "Link failure metrics for NOC dashboard KPI rollup", "access_count": 1460, "days_ago": 0},
        {"consumer_name": "NetworkInsightsApiDummy", "usage_type": "api", "description": "At-risk link scores for network insights API endpoint", "access_count": 4500, "days_ago": 0},
    ],
    "BandwidthCostReconciliation": [
        {"consumer_name": "BandwidthCostReconciliation", "usage_type": "etl", "description": None, "access_count": 4560, "days_ago": 0},
        {"consumer_name": "NocDashboardSnapshot", "usage_type": "etl", "description": "Bandwidth cost variance data for NOC dashboard", "access_count": 1120, "days_ago": 0},
        {"consumer_name": "BandwidthReportsApiDummy", "usage_type": "api", "description": "Reconciled bandwidth data for billing reports API", "access_count": 1890, "days_ago": 0},
    ],
    "NocDashboardSnapshot": [
        {"consumer_name": "NocDashboardSnapshot", "usage_type": "etl", "description": None, "access_count": 5340, "days_ago": 0},
    ],
    "IncidentAnalyticsRollup": [
        {"consumer_name": "IncidentAnalyticsRollup", "usage_type": "etl", "description": None, "access_count": 3890, "days_ago": 0},
    ],
    "NetworkInsightsApiDummy": [
        {"consumer_name": "NetworkInsightsApiDummy", "usage_type": "api", "description": None, "access_count": 9750, "days_ago": 0},
    ],
    "BandwidthReportsApiDummy": [
        {"consumer_name": "BandwidthReportsApiDummy", "usage_type": "api", "description": None, "access_count": 4120, "days_ago": 0},
    ],
}


async def seed_usage_data() -> None:
    """Insert enrichment usage data for dev if the table is empty."""
    try:
        async with async_session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(PipelineUsage))
            if count and count > 0:
                logger.info("Usage data already seeded (%d rows), skipping", count)
                return

            total = 0
            for etl_name, usages in SEED_USAGES.items():
                for u in usages:
                    usage = PipelineUsage(
                        id=uuid.uuid4(),
                        etl_name=etl_name,
                        consumer_name=u["consumer_name"],
                        usage_type=u["usage_type"],
                        description=u["description"],
                        access_count=u["access_count"],
                        last_accessed_at=datetime.now() - timedelta(days=u["days_ago"]),
                    )
                    session.add(usage)
                    total += 1

            await session.commit()
            logger.info("Seeded %d usage records for dev", total)
    except Exception:
        logger.exception("Failed to seed usage data")
