"""pulse_360 — Product analytics & user insights pipeline.

Ingests user behavior telemetry and core backend snapshots to power
product analytics dashboards. Runs every 4 hours.
"""

import ast
from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

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
    dag_id="pulse_360",
    default_args=default_args,
    description="Product analytics & user insights",
    schedule="0 */4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["analytics", "product", "dagger"],
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

    # Dependencies derived from task configs:
    # mixpanel_user_events needs postgres_production_db
    postgres_production_db >> mixpanel_user_events
