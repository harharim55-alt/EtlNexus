"""transit_exchange — Nightly network transit & peering exchange pipeline.

Consolidates switch port data, BGP route announcements, and DNS records
into a unified bandwidth billing picture. Runs daily at midnight UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_runner import run_etl

from daily.task_configs import (
    switch_port_collector_task_config,
    bgp_route_sync_task_config,
    bandwidth_billing_aggregator_task_config,
    dns_record_sync_task_config,
)
from daily.resources import (
    switch_port_collector_resources,
    bgp_route_sync_resources,
    bandwidth_billing_aggregator_resources,
    dns_record_sync_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="transit_exchange",
    default_args=default_args,
    description="Nightly network transit & peering exchange",
    schedule="0 0 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    switch_port_collector = PythonOperator(
        task_id="switch_port_collector",
        python_callable=run_etl,
        params={
            "etl_name": "switch_port_collector",
            "category": "Network Infrastructure",
            "schedule": "Daily at 03:00 UTC",
            "needs": [],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "switch_port_collector",
            "needs": [], "prefers": [],
            "category": "Network Infrastructure",
            "schedule": "Daily at 03:00 UTC",
            "resources": switch_port_collector_resources.resources,
        },
    )

    bgp_route_sync = PythonOperator(
        task_id="bgp_route_sync",
        python_callable=run_etl,
        params={
            "etl_name": "bgp_route_sync",
            "category": "Transit/Peering",
            "schedule": "Daily at 00:00 UTC",
            "needs": ["switch_port_collector"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "bgp_route_sync",
            "needs": ["switch_port_collector"], "prefers": [],
            "category": "Transit/Peering",
            "schedule": "Daily at 00:00 UTC",
            "resources": bgp_route_sync_resources.resources,
        },
    )

    bandwidth_billing_aggregator = PythonOperator(
        task_id="bandwidth_billing_aggregator",
        python_callable=run_etl,
        params={
            "etl_name": "bandwidth_billing_aggregator",
            "category": "Bandwidth/Billing",
            "schedule": "Hourly",
            "needs": ["bgp_route_sync"],
            "prefers": ["dns_record_sync"],
        },
        op_kwargs={
            "etl_name": "bandwidth_billing_aggregator",
            "needs": ["bgp_route_sync"], "prefers": ["dns_record_sync"],
            "category": "Bandwidth/Billing",
            "schedule": "Hourly",
            "resources": bandwidth_billing_aggregator_resources.resources,
        },
    )

    dns_record_sync = PythonOperator(
        task_id="dns_record_sync",
        python_callable=run_etl,
        params={
            "etl_name": "dns_record_sync",
            "category": "DNS/Resolution",
            "schedule": "Hourly",
            "needs": [],
            "prefers": ["switch_port_collector"],
        },
        op_kwargs={
            "etl_name": "dns_record_sync",
            "needs": [], "prefers": ["switch_port_collector"],
            "category": "DNS/Resolution",
            "schedule": "Hourly",
            "resources": dns_record_sync_resources.resources,
        },
    )

    # Dependencies derived from task configs:
    # switch_port_collector has no needs → runs first
    # bgp_route_sync needs switch_port_collector
    # dns_record_sync prefers switch_port_collector
    # bandwidth_billing_aggregator needs bgp_route_sync, prefers dns_record_sync
    switch_port_collector >> bgp_route_sync >> bandwidth_billing_aggregator
    switch_port_collector >> dns_record_sync >> bandwidth_billing_aggregator
