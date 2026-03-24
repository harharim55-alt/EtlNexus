"""peering_audit — Nightly peering audit — route table recon, bandwidth analysis, DNS intelligence.

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
    PortScanCollector_task_config,
    RouteTableRecon_task_config,
    BandwidthAnalyzer_task_config,
    DnsIntelSync_task_config,
)
from daily.resources import (
    PortScanCollector_resources,
    RouteTableRecon_resources,
    BandwidthAnalyzer_resources,
    DnsIntelSync_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="peering_audit",
    default_args=default_args,
    description="Nightly peering audit — route table recon, bandwidth analysis, DNS intelligence",
    schedule="0 0 * * *",
    start_date=datetime(2026, 3, 8),
    catchup=True,
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
        PortScanCollector = PythonOperator(
            task_id="PortScanCollector",
            python_callable=run_etl,
            params={
                "needs": PortScanCollector_task_config.needs,
                "prefers": PortScanCollector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "PortScanCollector",
                "resources": PortScanCollector_resources.resources,
            },
        )

        RouteTableRecon = PythonOperator(
            task_id="RouteTableRecon",
            python_callable=run_etl,
            params={
                "needs": RouteTableRecon_task_config.needs,
                "prefers": RouteTableRecon_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "RouteTableRecon",
                "resources": RouteTableRecon_resources.resources,
            },
        )

        BandwidthAnalyzer = PythonOperator(
            task_id="BandwidthAnalyzer",
            python_callable=run_etl,
            params={
                "needs": BandwidthAnalyzer_task_config.needs,
                "prefers": BandwidthAnalyzer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthAnalyzer",
                "resources": BandwidthAnalyzer_resources.resources,
            },
        )

        DnsIntelSync = PythonOperator(
            task_id="DnsIntelSync",
            python_callable=run_etl,
            params={
                "needs": DnsIntelSync_task_config.needs,
                "prefers": DnsIntelSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsIntelSync",
                "resources": DnsIntelSync_resources.resources,
            },
        )

    # Bouncer wiring
    SwitchTelemetryBouncer >> PortScanCollector
    BgpFeedBouncer >> RouteTableRecon
    DnsQueryLogBouncer >> DnsIntelSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "PortScanCollector": PortScanCollector,
        "RouteTableRecon": RouteTableRecon,
        "BandwidthAnalyzer": BandwidthAnalyzer,
        "DnsIntelSync": DnsIntelSync,
    }
    task_cfgs = {
        "PortScanCollector": PortScanCollector_task_config,
        "RouteTableRecon": RouteTableRecon_task_config,
        "BandwidthAnalyzer": BandwidthAnalyzer_task_config,
        "DnsIntelSync": DnsIntelSync_task_config,
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
