"""atlas_intelligence — Intelligence layer aggregation pipeline.

Builds enriched customer profiles, reconciles revenue, generates ML
churn features, and produces executive KPI snapshots. Runs daily at
01:00 UTC with deep dependency chains (depth 5).
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from daily import (
    postgres_production_db_task_config,
    shopify_sales_sync_task_config,
    salesforce_crm_sync_task_config,
    stripe_billing_aggregator_task_config,
    customer_360_enrichment_task_config,
    revenue_reconciliation_task_config,
    churn_prediction_features_task_config,
    executive_kpi_snapshot_task_config,
    customer_insights_api_task_config,
    billing_reports_api_task_config,
)
from hourly import mixpanel_user_events_task_config

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def run_etl(etl_name, **kwargs):
    print(f"ETL_START: {etl_name}")
    etl_path = Path(f"/data/etl-code/dagger/{etl_name}.py")
    suffixes = []
    if etl_path.exists():
        tree = ast.parse(etl_path.read_text())
        docstring = ast.get_docstring(tree)
        if docstring:
            print(f"ETL_DESCRIPTION: {docstring}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "SUFFIXES":
                        suffixes = ast.literal_eval(node.value)
    print(f"ETL_WRITES_TO: {etl_name}")
    for suffix in suffixes:
        print(f"ETL_WRITES_TO: {etl_name}_{suffix}")


with DAG(
    dag_id="atlas_intelligence",
    default_args=default_args,
    description="Intelligence layer aggregation — deep dependency chains",
    schedule="0 1 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["intelligence", "analytics", "ml", "dagger"],
) as dag:

    # --- Root layer (depth 0) ---
    postgres_production_db = PythonOperator(
        task_id="postgres_production_db",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "postgres_production_db",
            "needs": [], "prefers": [],
            "category": "Core Backend",
            "schedule": "Daily at 03:00 UTC",
        },
    )

    # --- Layer 1 (depth 1) ---
    shopify_sales_sync = PythonOperator(
        task_id="shopify_sales_sync",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "shopify_sales_sync",
            "needs": ["postgres_production_db"], "prefers": [],
            "category": "E-commerce",
            "schedule": "Daily at 00:00 UTC",
        },
    )

    salesforce_crm_sync = PythonOperator(
        task_id="salesforce_crm_sync",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "salesforce_crm_sync",
            "needs": [], "prefers": ["postgres_production_db"],
            "category": "Sales",
            "schedule": "Hourly",
        },
    )

    mixpanel_user_events = PythonOperator(
        task_id="mixpanel_user_events",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "mixpanel_user_events",
            "needs": ["postgres_production_db"], "prefers": [],
            "category": "Analytics",
            "schedule": "Every 4 Hours",
        },
    )

    # --- Layer 2 (depth 2) ---
    customer_360_enrichment = PythonOperator(
        task_id="customer_360_enrichment",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "customer_360_enrichment",
            "needs": ["postgres_production_db", "shopify_sales_sync"], "prefers": ["salesforce_crm_sync"],
            "category": "Analytics",
            "schedule": "Daily at 02:00 UTC",
        },
    )

    stripe_billing_aggregator = PythonOperator(
        task_id="stripe_billing_aggregator",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "stripe_billing_aggregator",
            "needs": ["shopify_sales_sync"], "prefers": ["salesforce_crm_sync"],
            "category": "Finance",
            "schedule": "Hourly",
        },
    )

    # --- Layer 3 (depth 3) ---
    churn_prediction_features = PythonOperator(
        task_id="churn_prediction_features",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "churn_prediction_features",
            "needs": ["customer_360_enrichment"], "prefers": ["mixpanel_user_events"],
            "category": "Machine Learning",
            "schedule": "Daily at 05:00 UTC",
        },
    )

    revenue_reconciliation = PythonOperator(
        task_id="revenue_reconciliation",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "revenue_reconciliation",
            "needs": ["stripe_billing_aggregator", "shopify_sales_sync"], "prefers": [],
            "category": "Finance",
            "schedule": "Daily at 04:00 UTC",
        },
    )

    # --- Layer 4 (depth 4) — leaf nodes ---
    executive_kpi_snapshot = PythonOperator(
        task_id="executive_kpi_snapshot",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "executive_kpi_snapshot",
            "needs": ["revenue_reconciliation", "churn_prediction_features"], "prefers": [],
            "category": "Executive",
            "schedule": "Daily at 06:00 UTC",
        },
    )

    customer_insights_api = PythonOperator(
        task_id="customer_insights_api",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "customer_insights_api",
            "needs": ["customer_360_enrichment", "churn_prediction_features"], "prefers": [],
            "category": "API",
            "schedule": "On-demand (API)",
        },
    )

    billing_reports_api = PythonOperator(
        task_id="billing_reports_api",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "billing_reports_api",
            "needs": ["revenue_reconciliation"], "prefers": ["stripe_billing_aggregator"],
            "category": "API",
            "schedule": "On-demand (API)",
        },
    )

    # --- Dependency wiring ---
    # Layer 0 → Layer 1
    postgres_production_db >> shopify_sales_sync
    postgres_production_db >> salesforce_crm_sync
    postgres_production_db >> mixpanel_user_events

    # Layer 1 → Layer 2
    shopify_sales_sync >> customer_360_enrichment
    salesforce_crm_sync >> customer_360_enrichment
    shopify_sales_sync >> stripe_billing_aggregator
    salesforce_crm_sync >> stripe_billing_aggregator

    # Layer 2 → Layer 3
    customer_360_enrichment >> churn_prediction_features
    mixpanel_user_events >> churn_prediction_features
    stripe_billing_aggregator >> revenue_reconciliation
    shopify_sales_sync >> revenue_reconciliation

    # Layer 3 → Layer 4
    churn_prediction_features >> executive_kpi_snapshot
    revenue_reconciliation >> executive_kpi_snapshot
    customer_360_enrichment >> customer_insights_api
    churn_prediction_features >> customer_insights_api
    revenue_reconciliation >> billing_reports_api
    stripe_billing_aggregator >> billing_reports_api
