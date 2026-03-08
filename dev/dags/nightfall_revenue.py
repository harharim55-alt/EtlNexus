"""nightfall_revenue — Nightly revenue & finance reconciliation.

Consolidates e-commerce transactions, billing events, and CRM data
into a unified revenue picture. Runs daily at midnight UTC.
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from daily import (
    postgres_production_db_task_config,
    shopify_sales_sync_task_config,
    stripe_billing_aggregator_task_config,
    salesforce_crm_sync_task_config,
)

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
    dag_id="nightfall_revenue",
    default_args=default_args,
    description="Nightly revenue & finance reconciliation",
    schedule="0 0 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["revenue", "finance", "dagger"],
) as dag:

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

    # Dependencies derived from task configs:
    # postgres_production_db has no needs → runs first
    # shopify_sales_sync needs postgres_production_db
    # salesforce_crm_sync prefers postgres_production_db
    # stripe_billing_aggregator needs shopify_sales_sync, prefers salesforce_crm_sync
    postgres_production_db >> shopify_sales_sync >> stripe_billing_aggregator
    postgres_production_db >> salesforce_crm_sync >> stripe_billing_aggregator
