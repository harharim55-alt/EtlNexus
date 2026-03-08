"""Mixpanel User Events — Every 4 hours analytics event processing."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


def extract(**kwargs):
    print("Extracting from raw_telemetry, core_backend")


def transform(**kwargs):
    print("Transforming user event data")


def load(**kwargs):
    print("Loading to fact_user_events, dim_sessions")


with DAG(
    dag_id="mixpanel_user_events",
    default_args=default_args,
    description="Analytics event processing every 4 hours",
    schedule_interval="0 */4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["analytics", "dagger"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=extract)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    t_extract >> t_transform >> t_load
