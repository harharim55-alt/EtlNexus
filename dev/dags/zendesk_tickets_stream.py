"""Zendesk Tickets Stream — Frequent ingestion of support tickets."""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


def extract(**kwargs):
    print("Extracting from tickets_stream, agent_events")


def transform(**kwargs):
    print("Transforming zendesk tickets data")


def load(**kwargs):
    print("Loading to raw_zendesk_tickets, raw_csat_scores")


with DAG(
    dag_id="zendesk_tickets_stream",
    default_args=default_args,
    description="Real-time streaming of customer support tickets",
    schedule_interval="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["support", "dagger"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=extract)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    t_extract >> t_transform >> t_load
