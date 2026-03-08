"""Stripe Billing Aggregator — Hourly subscription lifecycle aggregation."""

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
    print("Extracting from mixpanel_events, invoices, subscriptions")


def transform(**kwargs):
    print("Transforming billing aggregation data")


def load(**kwargs):
    print("Loading to finance_invoices, finance_subscriptions")


with DAG(
    dag_id="stripe_billing_aggregator",
    default_args=default_args,
    description="Aggregates subscription lifecycle events",
    schedule_interval="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["finance", "dagger"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=extract)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    t_extract >> t_transform >> t_load
