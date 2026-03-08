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
    "postgres_production_db": [
        {"consumer_name": "shopify_sales_sync", "usage_type": "etl", "description": "Syncs customer and order data from Shopify using production DB profiles", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "salesforce_crm_sync", "usage_type": "etl", "description": "Enriches CRM sync with production account data", "access_count": 4380, "days_ago": 0},
        {"consumer_name": "mixpanel_user_events", "usage_type": "etl", "description": "Maps event streams to production user profiles", "access_count": 2100, "days_ago": 0},
    ],
    "shopify_sales_sync": [
        {"consumer_name": "stripe_billing_aggregator", "usage_type": "etl", "description": "Aggregates billing data from Shopify orders", "access_count": 1847, "days_ago": 0},
        {"consumer_name": "customer_360_enrichment", "usage_type": "etl", "description": "Enriches customer profiles with purchase history", "access_count": 4200, "days_ago": 0},
        {"consumer_name": "revenue_reconciliation", "usage_type": "etl", "description": "Reconciles Shopify revenue against billing records", "access_count": 730, "days_ago": 0},
    ],
    "salesforce_crm_sync": [
        {"consumer_name": "stripe_billing_aggregator", "usage_type": "etl", "description": "Cross-references CRM deals with billing data", "access_count": 1234, "days_ago": 0},
        {"consumer_name": "customer_360_enrichment", "usage_type": "etl", "description": "Merges CRM contacts into unified customer view", "access_count": 1890, "days_ago": 0},
        {"consumer_name": "support_analytics_rollup", "usage_type": "etl", "description": "Correlates support tickets with CRM account health", "access_count": 445, "days_ago": 1},
    ],
    "mixpanel_user_events": [
        {"consumer_name": "churn_prediction_features", "usage_type": "etl", "description": "Behavioral event features for churn prediction model", "access_count": 3420, "days_ago": 0},
    ],
    "zendesk_tickets_stream": [
        {"consumer_name": "support_analytics_rollup", "usage_type": "etl", "description": "Aggregates ticket volume and SLA metrics", "access_count": 2103, "days_ago": 0},
    ],
    "stripe_billing_aggregator": [
        {"consumer_name": "revenue_reconciliation", "usage_type": "etl", "description": "Input to revenue variance and reconciliation analysis", "access_count": 956, "days_ago": 0},
        {"consumer_name": "billing_reports_api", "usage_type": "etl", "description": "Feeds aggregated billing data to API endpoint", "access_count": 365, "days_ago": 1},
    ],
    "customer_360_enrichment": [
        {"consumer_name": "churn_prediction_features", "usage_type": "etl", "description": "Customer health signals for churn feature pipeline", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "customer_insights_api", "usage_type": "etl", "description": "Serves enriched customer data via API", "access_count": 3200, "days_ago": 0},
    ],
    "churn_prediction_features": [
        {"consumer_name": "executive_kpi_snapshot", "usage_type": "etl", "description": "Churn metrics for executive KPI rollup", "access_count": 1460, "days_ago": 0},
        {"consumer_name": "customer_insights_api", "usage_type": "etl", "description": "At-risk customer scores for API endpoint", "access_count": 4500, "days_ago": 0},
    ],
    "revenue_reconciliation": [
        {"consumer_name": "executive_kpi_snapshot", "usage_type": "etl", "description": "Revenue variance data for executive dashboard", "access_count": 1120, "days_ago": 0},
        {"consumer_name": "billing_reports_api", "usage_type": "etl", "description": "Reconciled revenue data for billing reports API", "access_count": 1890, "days_ago": 0},
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
