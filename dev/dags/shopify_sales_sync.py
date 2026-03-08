"""Shopify Sales Sync — Daily e-commerce transaction sync."""

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
    print("Extracting from raw_orders, raw_customers, stripe_billing")


def transform(**kwargs):
    print("Transforming shopify sales data")


def load(**kwargs):
    print("Loading to stg_shopify_orders, stg_shopify_customers")


with DAG(
    dag_id="shopify_sales_sync",
    default_args=default_args,
    description="Daily synchronization of e-commerce transactions",
    schedule_interval="0 0 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["e-commerce", "dagger"],
) as dag:
    t_extract = PythonOperator(task_id="extract", python_callable=extract)
    t_transform = PythonOperator(task_id="transform", python_callable=transform)
    t_load = PythonOperator(task_id="load", python_callable=load)

    t_extract >> t_transform >> t_load
