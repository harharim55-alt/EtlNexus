"""Postgres Production DB — Daily core backend data snapshot."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}


def extract(**kwargs):
    print("Extracting from users, profiles, settings")


def transform(**kwargs):
    print("Transforming production DB snapshots")


def load(**kwargs):
    print("Loading to core_users_snapshot, core_profiles_snapshot")


with DAG(
    dag_id="postgres_production_db",
    default_args=default_args,
    description="Daily core backend data snapshot",
    schedule_interval="0 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["core-backend", "dagger"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=extract)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    t_extract >> t_transform >> t_load
