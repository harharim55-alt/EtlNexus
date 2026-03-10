"""Seed pipeline_usages table with enrichment data for downstream consumers."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.pipeline_usage import PipelineUsage

logger = logging.getLogger(__name__)

# Enrichment data keyed by etl_name → list of downstream consumer entries.
# consumer_name values match actual Airflow downstream task_ids.
SEED_USAGES: dict[str, list[dict]] = {
    "switch_port_collector": [
        {"consumer_name": "bgp_route_sync", "usage_type": "etl", "description": "Syncs BGP route tables using switch port interface data", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "dns_record_sync", "usage_type": "etl", "description": "Enriches DNS zone sync with port-level network topology", "access_count": 4380, "days_ago": 0},
        {"consumer_name": "netflow_capture", "usage_type": "etl", "description": "Maps NetFlow records to physical switch port interfaces", "access_count": 2100, "days_ago": 0},
    ],
    "bgp_route_sync": [
        {"consumer_name": "bandwidth_billing_aggregator", "usage_type": "etl", "description": "Aggregates bandwidth billing from BGP route announcements", "access_count": 1847, "days_ago": 0},
        {"consumer_name": "device_fingerprint_enrichment", "usage_type": "etl", "description": "Enriches device fingerprints with BGP routing context", "access_count": 4200, "days_ago": 0},
        {"consumer_name": "bandwidth_cost_reconciliation", "usage_type": "etl", "description": "Reconciles metered bandwidth against BGP route records", "access_count": 730, "days_ago": 0},
    ],
    "dns_record_sync": [
        {"consumer_name": "bandwidth_billing_aggregator", "usage_type": "etl", "description": "Cross-references DNS zones with bandwidth billing data", "access_count": 1234, "days_ago": 0},
        {"consumer_name": "device_fingerprint_enrichment", "usage_type": "etl", "description": "Merges DNS resolution data into unified device profiles", "access_count": 1890, "days_ago": 0},
        {"consumer_name": "incident_analytics_rollup", "usage_type": "etl", "description": "Correlates syslog incidents with DNS resolution context", "access_count": 445, "days_ago": 1},
    ],
    "netflow_capture": [
        {"consumer_name": "link_failure_prediction", "usage_type": "etl", "description": "Flow-level traffic features for link failure prediction model", "access_count": 3420, "days_ago": 0},
    ],
    "syslog_event_stream": [
        {"consumer_name": "incident_analytics_rollup", "usage_type": "etl", "description": "Aggregates syslog event volume and severity metrics", "access_count": 2103, "days_ago": 0},
    ],
    "bandwidth_billing_aggregator": [
        {"consumer_name": "bandwidth_cost_reconciliation", "usage_type": "etl", "description": "Input to bandwidth variance and cost reconciliation analysis", "access_count": 956, "days_ago": 0},
        {"consumer_name": "bandwidth_reports_api", "usage_type": "etl", "description": "Feeds aggregated bandwidth data to reports API endpoint", "access_count": 365, "days_ago": 1},
    ],
    "device_fingerprint_enrichment": [
        {"consumer_name": "link_failure_prediction", "usage_type": "etl", "description": "Device health signals for link failure feature pipeline", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "network_insights_api", "usage_type": "etl", "description": "Serves enriched device data via network insights API", "access_count": 3200, "days_ago": 0},
    ],
    "link_failure_prediction": [
        {"consumer_name": "noc_dashboard_snapshot", "usage_type": "etl", "description": "Link failure metrics for NOC dashboard KPI rollup", "access_count": 1460, "days_ago": 0},
        {"consumer_name": "network_insights_api", "usage_type": "etl", "description": "At-risk link scores for network insights API endpoint", "access_count": 4500, "days_ago": 0},
    ],
    "bandwidth_cost_reconciliation": [
        {"consumer_name": "noc_dashboard_snapshot", "usage_type": "etl", "description": "Bandwidth cost variance data for NOC dashboard", "access_count": 1120, "days_ago": 0},
        {"consumer_name": "bandwidth_reports_api", "usage_type": "etl", "description": "Reconciled bandwidth data for billing reports API", "access_count": 1890, "days_ago": 0},
    ],
    # Leaf pipelines — no downstream consumers, no seed entries
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
