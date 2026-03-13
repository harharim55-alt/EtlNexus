"""transit_exchange — Nightly network transit & peering exchange pipeline.

Consolidates switch port data, BGP route announcements, and DNS records
into a unified bandwidth billing picture. Runs daily at midnight UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_sensor

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

    # --- Single Relay group (sensors + ETLs) ---
    with TaskGroup("Relay", prefix_group_id=True) as relay:
        SwitchTelemetrySensor = PythonOperator(
            task_id="SwitchTelemetrySensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "SwitchTelemetrySensor",
                "team": "Dagger",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
            },
            op_kwargs={
                "sensor_name": "SwitchTelemetrySensor",
                "team": "Dagger",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
                "volume_per_day": 2_400_000,
            },
        )

        BgpFeedSensor = PythonOperator(
            task_id="BgpFeedSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "BgpFeedSensor",
                "team": "Dagger",
                "description": "Ingests BGP route announcements from peering routers",
            },
            op_kwargs={
                "sensor_name": "BgpFeedSensor",
                "team": "Dagger",
                "description": "Ingests BGP route announcements from peering routers",
                "volume_per_day": 850_000,
            },
        )

        DnsQueryLogSensor = PythonOperator(
            task_id="DnsQueryLogSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "DnsQueryLogSensor",
                "team": "Prism",
                "description": "Taps DNS resolver query logs for resolution analytics",
            },
            op_kwargs={
                "sensor_name": "DnsQueryLogSensor",
                "team": "Prism",
                "description": "Taps DNS resolver query logs for resolution analytics",
                "volume_per_day": 12_000_000,
            },
        )

        # --- ETL tasks ---
        SwitchPortCollector = PythonOperator(
            task_id="SwitchPortCollector",
            python_callable=run_etl,
            params={
                "etl_name": "SwitchPortCollector",
                "category": "Network Infrastructure",
                "schedule": "Daily at 03:00 UTC",
                "needs": SwitchPortCollector_task_config.needs,
                "prefers": SwitchPortCollector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SwitchPortCollector",
                "needs": SwitchPortCollector_task_config.needs, "prefers": SwitchPortCollector_task_config.prefers,
                "category": "Network Infrastructure",
                "schedule": "Daily at 03:00 UTC",
                "resources": SwitchPortCollector_resources.resources,
            },
        )

        BgpRouteSync = PythonOperator(
            task_id="BgpRouteSync",
            python_callable=run_etl,
            params={
                "etl_name": "BgpRouteSync",
                "category": "Transit/Peering",
                "schedule": "Daily at 00:00 UTC",
                "needs": BgpRouteSync_task_config.needs,
                "prefers": BgpRouteSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BgpRouteSync",
                "needs": BgpRouteSync_task_config.needs, "prefers": BgpRouteSync_task_config.prefers,
                "category": "Transit/Peering",
                "schedule": "Daily at 00:00 UTC",
                "resources": BgpRouteSync_resources.resources,
            },
        )

        BandwidthBillingAggregator = PythonOperator(
            task_id="BandwidthBillingAggregator",
            python_callable=run_etl,
            params={
                "etl_name": "BandwidthBillingAggregator",
                "category": "Bandwidth/Billing",
                "schedule": "Hourly",
                "needs": BandwidthBillingAggregator_task_config.needs,
                "prefers": BandwidthBillingAggregator_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthBillingAggregator",
                "needs": BandwidthBillingAggregator_task_config.needs, "prefers": BandwidthBillingAggregator_task_config.prefers,
                "category": "Bandwidth/Billing",
                "schedule": "Hourly",
                "resources": BandwidthBillingAggregator_resources.resources,
            },
        )

        DnsRecordSync = PythonOperator(
            task_id="DnsRecordSync",
            python_callable=run_etl,
            params={
                "etl_name": "DnsRecordSync",
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "needs": DnsRecordSync_task_config.needs,
                "prefers": DnsRecordSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsRecordSync",
                "needs": DnsRecordSync_task_config.needs, "prefers": DnsRecordSync_task_config.prefers,
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "resources": DnsRecordSync_resources.resources,
            },
        )

    # Sensor wiring
    SwitchTelemetrySensor >> SwitchPortCollector
    BgpFeedSensor >> BgpRouteSync
    DnsQueryLogSensor >> DnsRecordSync

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
