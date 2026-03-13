"""transit_exchange — Nightly network transit & peering exchange pipeline.

Consolidates switch port data, BGP route announcements, and DNS records
into a unified bandwidth billing picture. Runs daily at midnight UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

from daily.task_configs import (
    SwitchPortCollector_task_config,
    BgpRouteSync_task_config,
    BandwidthBillingAggregator_task_config,
    DnsRecordSync_task_config,
)
from daily.resources import (
    SwitchPortCollector_resources,
    BgpRouteSync_resources,
    BandwidthBillingAggregator_resources,
    DnsRecordSync_resources,
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

    # --- Single Relay group (bouncers + ETLs) ---
    with TaskGroup("Relay", prefix_group_id=True) as relay:
        SwitchTelemetryBouncer = PythonOperator(
            task_id="SwitchTelemetryBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SwitchTelemetryBouncer",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
            },
        )

        BgpFeedBouncer = PythonOperator(
            task_id="BgpFeedBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "BgpFeedBouncer",
                "description": "Ingests BGP route announcements from peering routers",
            },
        )

        DnsQueryLogBouncer = PythonOperator(
            task_id="DnsQueryLogBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "DnsQueryLogBouncer",
                "description": "Taps DNS resolver query logs for resolution analytics",
            },
        )

        # --- ETL tasks ---
        SwitchPortCollector = PythonOperator(
            task_id="SwitchPortCollector",
            python_callable=run_etl,
            params={
                "needs": SwitchPortCollector_task_config.needs,
                "prefers": SwitchPortCollector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SwitchPortCollector",
                "resources": SwitchPortCollector_resources.resources,
            },
        )

        BgpRouteSync = PythonOperator(
            task_id="BgpRouteSync",
            python_callable=run_etl,
            params={
                "needs": BgpRouteSync_task_config.needs,
                "prefers": BgpRouteSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BgpRouteSync",
                "resources": BgpRouteSync_resources.resources,
            },
        )

        BandwidthBillingAggregator = PythonOperator(
            task_id="BandwidthBillingAggregator",
            python_callable=run_etl,
            params={
                "needs": BandwidthBillingAggregator_task_config.needs,
                "prefers": BandwidthBillingAggregator_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthBillingAggregator",
                "resources": BandwidthBillingAggregator_resources.resources,
            },
        )

        DnsRecordSync = PythonOperator(
            task_id="DnsRecordSync",
            python_callable=run_etl,
            params={
                "needs": DnsRecordSync_task_config.needs,
                "prefers": DnsRecordSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsRecordSync",
                "resources": DnsRecordSync_resources.resources,
            },
        )

    # Bouncer wiring
    SwitchTelemetryBouncer >> SwitchPortCollector
    BgpFeedBouncer >> BgpRouteSync
    DnsQueryLogBouncer >> DnsRecordSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SwitchPortCollector": SwitchPortCollector,
        "BgpRouteSync": BgpRouteSync,
        "BandwidthBillingAggregator": BandwidthBillingAggregator,
        "DnsRecordSync": DnsRecordSync,
    }
    task_cfgs = {
        "SwitchPortCollector": SwitchPortCollector_task_config,
        "BgpRouteSync": BgpRouteSync_task_config,
        "BandwidthBillingAggregator": BandwidthBillingAggregator_task_config,
        "DnsRecordSync": DnsRecordSync_task_config,
    }
    for task_id, op in etl_ops.items():
        tc = task_cfgs[task_id]
        for need in tc.needs:
            if need in etl_ops:
                etl_ops[need] >> op
        for prefer in tc.prefers:
            if prefer in etl_ops:
                etl_ops[prefer] >> op
        if any(p in etl_ops for p in tc.prefers):
            op.trigger_rule = "all_done"
