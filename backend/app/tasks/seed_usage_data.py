"""Seed pipeline_usages table with enrichment data for downstream consumers and self-read counts."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.pipeline_usage import PipelineUsage

logger = logging.getLogger(__name__)

# Enrichment data keyed by etl_name → list of entries.
# First entry per ETL is a self-entry (consumer_name = etl_name) for the ETL's own read count.
# Remaining entries are downstream consumers (consumer_name = Airflow downstream task_id).
SEED_USAGES: dict[str, list[dict]] = {
    "PortScanCollector": [
        {"consumer_name": "PortScanCollector", "usage_type": "etl", "description": None, "access_count": 18200, "days_ago": 0},
        {"consumer_name": "RouteTableRecon", "usage_type": "etl", "description": "Syncs route tables using port scan interface data", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "DnsIntelSync", "usage_type": "etl", "description": "Enriches DNS intel sync with port-level network topology", "access_count": 4380, "days_ago": 0},
        {"consumer_name": "FlowInterceptor", "usage_type": "etl", "description": "Maps intercepted flow records to physical port interfaces", "access_count": 2100, "days_ago": 0},
    ],
    "RouteTableRecon": [
        {"consumer_name": "RouteTableRecon", "usage_type": "etl", "description": None, "access_count": 9450, "days_ago": 0},
        {"consumer_name": "BandwidthAnalyzer", "usage_type": "etl", "description": "Analyzes bandwidth usage from route table recon announcements", "access_count": 1847, "days_ago": 0},
        {"consumer_name": "DeviceFingerprinter", "usage_type": "etl", "description": "Enriches device fingerprints with route recon context", "access_count": 4200, "days_ago": 0},
        {"consumer_name": "BandwidthAuditReconciler", "usage_type": "etl", "description": "Reconciles metered bandwidth against route recon records", "access_count": 730, "days_ago": 0},
    ],
    "DnsIntelSync": [
        {"consumer_name": "DnsIntelSync", "usage_type": "etl", "description": None, "access_count": 5120, "days_ago": 0},
        {"consumer_name": "BandwidthAnalyzer", "usage_type": "etl", "description": "Cross-references DNS intel zones with bandwidth analysis data", "access_count": 1234, "days_ago": 0},
        {"consumer_name": "DeviceFingerprinter", "usage_type": "etl", "description": "Merges DNS intel resolution data into unified device profiles", "access_count": 1890, "days_ago": 0},
        {"consumer_name": "IncidentForensicsRollup", "usage_type": "etl", "description": "Correlates forensic incidents with DNS intel resolution context", "access_count": 445, "days_ago": 1},
    ],
    "FlowInterceptor": [
        {"consumer_name": "FlowInterceptor", "usage_type": "etl", "description": None, "access_count": 7630, "days_ago": 0},
        {"consumer_name": "LinkAnomalyDetector", "usage_type": "etl", "description": "Flow-level traffic features for link anomaly detection model", "access_count": 3420, "days_ago": 0},
    ],
    "SyslogCollector": [
        {"consumer_name": "SyslogCollector", "usage_type": "etl", "description": None, "access_count": 12400, "days_ago": 0},
        {"consumer_name": "IncidentForensicsRollup", "usage_type": "etl", "description": "Aggregates syslog event volume and severity metrics for forensics", "access_count": 2103, "days_ago": 0},
    ],
    "BandwidthAnalyzer": [
        {"consumer_name": "BandwidthAnalyzer", "usage_type": "etl", "description": None, "access_count": 3780, "days_ago": 0},
        {"consumer_name": "BandwidthAuditReconciler", "usage_type": "etl", "description": "Input to bandwidth variance and audit reconciliation analysis", "access_count": 956, "days_ago": 0},
        {"consumer_name": "BandwidthAuditApiDummy", "usage_type": "api", "description": "Feeds analyzed bandwidth data to audit reports API endpoint", "access_count": 365, "days_ago": 1},
    ],
    "DeviceFingerprinter": [
        {"consumer_name": "DeviceFingerprinter", "usage_type": "etl", "description": None, "access_count": 6890, "days_ago": 0},
        {"consumer_name": "LinkAnomalyDetector", "usage_type": "etl", "description": "Device health signals for link anomaly detection feature pipeline", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "NetworkIntelApiDummy", "usage_type": "api", "description": "Serves fingerprinted device data via network intel API", "access_count": 3200, "days_ago": 0},
    ],
    "LinkAnomalyDetector": [
        {"consumer_name": "LinkAnomalyDetector", "usage_type": "etl", "description": None, "access_count": 8210, "days_ago": 0},
        {"consumer_name": "NocThreatSnapshot", "usage_type": "etl", "description": "Link anomaly metrics for NOC threat snapshot KPI rollup", "access_count": 1460, "days_ago": 0},
        {"consumer_name": "NetworkIntelApiDummy", "usage_type": "api", "description": "At-risk link threat scores for network intel API endpoint", "access_count": 4500, "days_ago": 0},
    ],
    "BandwidthAuditReconciler": [
        {"consumer_name": "BandwidthAuditReconciler", "usage_type": "etl", "description": None, "access_count": 4560, "days_ago": 0},
        {"consumer_name": "NocThreatSnapshot", "usage_type": "etl", "description": "Bandwidth audit variance data for NOC threat snapshot", "access_count": 1120, "days_ago": 0},
        {"consumer_name": "BandwidthAuditApiDummy", "usage_type": "api", "description": "Reconciled bandwidth data for audit billing reports API", "access_count": 1890, "days_ago": 0},
    ],
    "NocThreatSnapshot": [
        {"consumer_name": "NocThreatSnapshot", "usage_type": "etl", "description": None, "access_count": 5340, "days_ago": 0},
    ],
    "IncidentForensicsRollup": [
        {"consumer_name": "IncidentForensicsRollup", "usage_type": "etl", "description": None, "access_count": 3890, "days_ago": 0},
    ],
    "NetworkIntelApiDummy": [
        {"consumer_name": "NetworkIntelApiDummy", "usage_type": "api", "description": None, "access_count": 9750, "days_ago": 0},
    ],
    "BandwidthAuditApiDummy": [
        {"consumer_name": "BandwidthAuditApiDummy", "usage_type": "api", "description": None, "access_count": 4120, "days_ago": 0},
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
                        last_accessed_at=datetime.now(UTC) - timedelta(days=u["days_ago"]),
                    )
                    session.add(usage)
                    total += 1

            await session.commit()
            logger.info("Seeded %d usage records for dev", total)
    except Exception:
        logger.exception("Failed to seed usage data")
