"""watchtower — Customer ops & support monitoring pipeline.

Monitors support ticket flow and CRM activity to keep operations
teams informed. Runs hourly.
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from hourly import zendesk_tickets_stream_task_config, support_analytics_rollup_task_config

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
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
    dag_id="watchtower",
    default_args=default_args,
    description="Customer ops & support monitoring",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["support", "ops", "dagger"],
) as dag:

    zendesk_tickets_stream = PythonOperator(
        task_id="zendesk_tickets_stream",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "zendesk_tickets_stream",
            "needs": [], "prefers": ["salesforce_crm_sync"],
            "category": "Support",
            "schedule": "Real-time (Streaming)",
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

    support_analytics_rollup = PythonOperator(
        task_id="support_analytics_rollup",
        python_callable=run_etl,
        op_kwargs={
            "etl_name": "support_analytics_rollup",
            "needs": ["zendesk_tickets_stream"], "prefers": ["salesforce_crm_sync"],
            "category": "Support",
            "schedule": "Hourly",
        },
    )

    # Dependencies derived from task configs:
    # zendesk_tickets_stream prefers salesforce_crm_sync (soft dep)
    # support_analytics_rollup needs zendesk, prefers salesforce
    zendesk_tickets_stream >> support_analytics_rollup
    salesforce_crm_sync >> support_analytics_rollup
