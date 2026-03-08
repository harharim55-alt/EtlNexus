"""Seed pipeline_usages table with sample dev data if empty."""

import logging
import uuid
from datetime import datetime, timedelta

from sqlalchemy import func, select

from app.database import async_session_factory
from app.models.pipeline import Pipeline
from app.models.pipeline_usage import PipelineUsage

logger = logging.getLogger(__name__)

# Sample usage data keyed by pipeline name (lowercase, underscored)
SEED_USAGES: dict[str, list[dict]] = {
    "shopify_sales_sync": [
        {"consumer_name": "Revenue Dashboard", "usage_type": "dashboard", "description": "Daily GMV and order metrics", "access_count": 1847, "days_ago": 0},
        {"consumer_name": "Finance Team", "usage_type": "import", "description": "Monthly revenue reconciliation", "access_count": 312, "days_ago": 1},
        {"consumer_name": "product_recommendation_model", "usage_type": "downstream", "description": "ML feature pipeline for purchase history", "access_count": 4200, "days_ago": 0},
        {"consumer_name": "Data Warehouse", "usage_type": "catalog_query", "description": "Nightly aggregation into dim_orders", "access_count": 730, "days_ago": 0},
    ],
    "zendesk_tickets_stream": [
        {"consumer_name": "Support Ops Dashboard", "usage_type": "dashboard", "description": "Real-time ticket volume and SLA tracking", "access_count": 2103, "days_ago": 0},
        {"consumer_name": "CX Analytics Team", "usage_type": "import", "description": "Weekly CSAT analysis", "access_count": 89, "days_ago": 3},
        {"consumer_name": "churn_prediction_model", "usage_type": "downstream", "description": "Ticket sentiment features for churn model", "access_count": 1560, "days_ago": 0},
    ],
    "stripe_billing_aggregator": [
        {"consumer_name": "Finance Dashboard", "usage_type": "dashboard", "description": "MRR, ARR, and churn metrics", "access_count": 956, "days_ago": 0},
        {"consumer_name": "Accounting Team", "usage_type": "import", "description": "Quarterly revenue recognition", "access_count": 45, "days_ago": 7},
        {"consumer_name": "Revenue Forecast Pipeline", "usage_type": "downstream", "description": "Input to billing forecast model", "access_count": 365, "days_ago": 1},
        {"consumer_name": "Investor Reporting", "usage_type": "catalog_query", "description": "Board-level financial summaries", "access_count": 24, "days_ago": 14},
        {"consumer_name": "tax_compliance_etl", "usage_type": "downstream", "description": "Tax jurisdiction calculations", "access_count": 180, "days_ago": 2},
    ],
    "mixpanel_user_events": [
        {"consumer_name": "Product Analytics Dashboard", "usage_type": "dashboard", "description": "Funnel conversion and feature adoption", "access_count": 3420, "days_ago": 0},
        {"consumer_name": "Growth Team", "usage_type": "import", "description": "A/B test analysis and experimentation", "access_count": 678, "days_ago": 0},
        {"consumer_name": "user_segmentation_pipeline", "usage_type": "downstream", "description": "Behavioral cohort generation", "access_count": 2890, "days_ago": 0},
    ],
    "salesforce_crm_sync": [
        {"consumer_name": "Sales Dashboard", "usage_type": "dashboard", "description": "Pipeline value and win rate tracking", "access_count": 1234, "days_ago": 0},
        {"consumer_name": "Sales Ops Team", "usage_type": "import", "description": "Territory assignment updates", "access_count": 156, "days_ago": 2},
        {"consumer_name": "lead_scoring_model", "usage_type": "downstream", "description": "ML model for lead qualification", "access_count": 1890, "days_ago": 0},
        {"consumer_name": "Marketing Attribution", "usage_type": "catalog_query", "description": "Campaign ROI by deal stage", "access_count": 445, "days_ago": 1},
    ],
    "postgres_production_db": [
        {"consumer_name": "Core Backend API", "usage_type": "import", "description": "Primary data source for application tables", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "Data Warehouse", "usage_type": "downstream", "description": "CDC replication into analytics warehouse", "access_count": 4380, "days_ago": 0},
        {"consumer_name": "Monitoring Dashboard", "usage_type": "dashboard", "description": "Database health and query performance", "access_count": 2100, "days_ago": 0},
    ],
    "customer_360_enrichment": [
        {"consumer_name": "Customer Success Platform", "usage_type": "dashboard", "description": "Unified customer health overview", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "Marketing Team", "usage_type": "import", "description": "Segment-based campaign targeting", "access_count": 567, "days_ago": 1},
        {"consumer_name": "churn_prediction_features", "usage_type": "downstream", "description": "Input to ML churn feature pipeline", "access_count": 1460, "days_ago": 0},
        {"consumer_name": "customer_insights_api", "usage_type": "downstream", "description": "Customer data API endpoint", "access_count": 3200, "days_ago": 0},
    ],
    "revenue_reconciliation": [
        {"consumer_name": "Finance Reconciliation Dashboard", "usage_type": "dashboard", "description": "Revenue variance and discrepancy tracking", "access_count": 1120, "days_ago": 0},
        {"consumer_name": "CFO Weekly Report", "usage_type": "import", "description": "Executive financial summary", "access_count": 52, "days_ago": 3},
        {"consumer_name": "executive_kpi_snapshot", "usage_type": "downstream", "description": "Input to executive KPI rollup", "access_count": 730, "days_ago": 0},
        {"consumer_name": "billing_reports_api", "usage_type": "downstream", "description": "Billing data API endpoint", "access_count": 1890, "days_ago": 0},
    ],
    "churn_prediction_features": [
        {"consumer_name": "ML Platform", "usage_type": "downstream", "description": "Feature store for churn prediction model", "access_count": 4500, "days_ago": 0},
        {"consumer_name": "Customer Success Team", "usage_type": "dashboard", "description": "At-risk customer identification", "access_count": 890, "days_ago": 0},
        {"consumer_name": "Retention Campaign Engine", "usage_type": "import", "description": "Automated retention intervention triggers", "access_count": 2100, "days_ago": 0},
    ],
    "support_analytics_rollup": [
        {"consumer_name": "Support Ops Dashboard", "usage_type": "dashboard", "description": "Agent performance and SLA metrics", "access_count": 1560, "days_ago": 0},
        {"consumer_name": "VP Support Weekly Review", "usage_type": "import", "description": "Weekly support operations summary", "access_count": 78, "days_ago": 2},
        {"consumer_name": "Workforce Planning", "usage_type": "catalog_query", "description": "Staffing and scheduling optimization", "access_count": 340, "days_ago": 1},
    ],
    "executive_kpi_snapshot": [
        {"consumer_name": "Executive Dashboard", "usage_type": "dashboard", "description": "C-suite KPI overview", "access_count": 456, "days_ago": 0},
        {"consumer_name": "Board Deck Generator", "usage_type": "import", "description": "Quarterly board presentation data", "access_count": 12, "days_ago": 14},
        {"consumer_name": "Investor Relations", "usage_type": "catalog_query", "description": "Key metrics for investor updates", "access_count": 89, "days_ago": 7},
    ],
    "customer_insights_api": [
        {"consumer_name": "Product Frontend", "usage_type": "import", "description": "In-app customer health widgets", "access_count": 12400, "days_ago": 0},
        {"consumer_name": "Mobile App", "usage_type": "import", "description": "Customer segment-based personalization", "access_count": 8900, "days_ago": 0},
        {"consumer_name": "Customer Success CRM Plugin", "usage_type": "downstream", "description": "Real-time health scores in CRM", "access_count": 3400, "days_ago": 0},
    ],
    "billing_reports_api": [
        {"consumer_name": "Finance Portal", "usage_type": "import", "description": "Self-service billing reports for finance team", "access_count": 2340, "days_ago": 0},
        {"consumer_name": "Accounting Integration", "usage_type": "downstream", "description": "Automated journal entry generation", "access_count": 1200, "days_ago": 0},
        {"consumer_name": "Tax Compliance System", "usage_type": "import", "description": "Revenue data for tax calculations", "access_count": 365, "days_ago": 1},
    ],
}


async def seed_usage_data() -> None:
    """Insert sample usage data for dev pipelines if the table is empty."""
    try:
        async with async_session_factory() as session:
            count = await session.scalar(select(func.count()).select_from(PipelineUsage))
            if count and count > 0:
                logger.info("Usage data already seeded (%d rows), skipping", count)
                return

            pipelines = (await session.execute(select(Pipeline))).scalars().all()
            pipeline_map = {p.name.lower().replace(" ", "_"): p for p in pipelines}

            total = 0
            for etl_key, usages in SEED_USAGES.items():
                pipeline = pipeline_map.get(etl_key)
                if not pipeline:
                    continue
                for u in usages:
                    usage = PipelineUsage(
                        id=uuid.uuid4(),
                        pipeline_id=pipeline.id,
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
