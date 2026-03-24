"""network_recon — Network reconnaissance — device fingerprinting, link anomaly detection, bandwidth forensics.

Builds enriched device profiles, reconciles bandwidth costs, generates ML
link anomaly detection, and produces NOC threat snapshots. Runs daily at
01:00 UTC with deep dependency chains (depth 5).
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
    DnsIntelSync_task_config,
    BandwidthAnalyzer_task_config,
    DeviceFingerprinter_task_config,
    BandwidthAuditReconciler_task_config,
    LinkAnomalyDetector_task_config,
    NocThreatSnapshot_task_config,
    NetworkIntelApiDummy_task_config,
    BandwidthAuditApiDummy_task_config,
    NetworkThreatAssessment_task_config,
)
from hourly.task_configs import FlowInterceptor_task_config
from daily.resources import (
    PortScanCollector_resources,
    RouteTableRecon_resources,
    DnsIntelSync_resources,
    BandwidthAnalyzer_resources,
    DeviceFingerprinter_resources,
    BandwidthAuditReconciler_resources,
    LinkAnomalyDetector_resources,
    NocThreatSnapshot_resources,
    NetworkIntelApiDummy_resources,
    BandwidthAuditApiDummy_resources,
    NetworkThreatAssessment_resources,
)
from hourly.resources import FlowInterceptor_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="network_recon",
    default_args=default_args,
    description="Network reconnaissance — device fingerprinting, link anomaly detection, bandwidth forensics",
    schedule="0 1 * * *",
    start_date=datetime(2026, 3, 8),
    catchup=True,
) as dag:

    # --- Bouncers group (data ingestion) ---
    with TaskGroup("Dagger-Bouncers", prefix_group_id=True) as bouncers:
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

        NetflowCollectorBouncer = PythonOperator(
            task_id="NetflowCollectorBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "NetflowCollectorBouncer",
                "description": "Captures NetFlow/sFlow records from edge routers",
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

    # --- Collection group (depth 0-1) ---
    with TaskGroup("Dagger-Collection", prefix_group_id=True) as collection:
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

        FlowInterceptor = PythonOperator(
            task_id="FlowInterceptor",
            python_callable=run_etl,
            params={
                "needs": FlowInterceptor_task_config.needs,
                "prefers": FlowInterceptor_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "FlowInterceptor",
                "resources": FlowInterceptor_resources.resources,
            },
        )

    # --- Oasis cross-DAG tasks ---
    with TaskGroup("Oasis-Collection", prefix_group_id=True) as oasis_collection:
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

    # --- Enrichment group (depth 2-3) ---
    with TaskGroup("Dagger-Enrichment", prefix_group_id=True) as enrichment:
        DeviceFingerprinter = PythonOperator(
            task_id="DeviceFingerprinter",
            python_callable=run_etl,
            params={
                "needs": DeviceFingerprinter_task_config.needs,
                "prefers": DeviceFingerprinter_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeviceFingerprinter",
                "resources": DeviceFingerprinter_resources.resources,
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

        LinkAnomalyDetector = PythonOperator(
            task_id="LinkAnomalyDetector",
            python_callable=run_etl,
            params={
                "needs": LinkAnomalyDetector_task_config.needs,
                "prefers": LinkAnomalyDetector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "LinkAnomalyDetector",
                "resources": LinkAnomalyDetector_resources.resources,
            },
        )

        BandwidthAuditReconciler = PythonOperator(
            task_id="BandwidthAuditReconciler",
            python_callable=run_etl,
            params={
                "needs": BandwidthAuditReconciler_task_config.needs,
                "prefers": BandwidthAuditReconciler_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthAuditReconciler",
                "resources": BandwidthAuditReconciler_resources.resources,
            },
        )

    # --- Assessment group (depth 3-4) — comprehensive analysis ---
    with TaskGroup("Dagger-Assessment", prefix_group_id=True) as assessment:
        NetworkThreatAssessment = PythonOperator(
            task_id="NetworkThreatAssessment",
            python_callable=run_etl,
            params={
                "needs": NetworkThreatAssessment_task_config.needs,
                "prefers": NetworkThreatAssessment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetworkThreatAssessment",
                "resources": NetworkThreatAssessment_resources.resources,
            },
        )

    # --- Delivery group (depth 4) — leaf nodes ---
    with TaskGroup("Dagger-Delivery", prefix_group_id=True) as delivery:
        NocThreatSnapshot = PythonOperator(
            task_id="NocThreatSnapshot",
            python_callable=run_etl,
            params={
                "needs": NocThreatSnapshot_task_config.needs,
                "prefers": NocThreatSnapshot_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NocThreatSnapshot",
                "resources": NocThreatSnapshot_resources.resources,
            },
        )

        NetworkIntelApiDummy = PythonOperator(
            task_id="NetworkIntelApiDummy",
            python_callable=run_etl,
            params={
                "needs": NetworkIntelApiDummy_task_config.needs,
                "prefers": NetworkIntelApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetworkIntelApiDummy",
                "resources": NetworkIntelApiDummy_resources.resources,
            },
        )

        BandwidthAuditApiDummy = PythonOperator(
            task_id="BandwidthAuditApiDummy",
            python_callable=run_etl,
            params={
                "needs": BandwidthAuditApiDummy_task_config.needs,
                "prefers": BandwidthAuditApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthAuditApiDummy",
                "resources": BandwidthAuditApiDummy_resources.resources,
            },
        )

    # --- Bouncer wiring (bouncers → root ETL tasks) ---
    SwitchTelemetryBouncer >> PortScanCollector
    BgpFeedBouncer >> RouteTableRecon
    NetflowCollectorBouncer >> FlowInterceptor
    DnsQueryLogBouncer >> DnsIntelSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "PortScanCollector": PortScanCollector,
        "RouteTableRecon": RouteTableRecon,
        "DnsIntelSync": DnsIntelSync,
        "FlowInterceptor": FlowInterceptor,
        "DeviceFingerprinter": DeviceFingerprinter,
        "BandwidthAnalyzer": BandwidthAnalyzer,
        "LinkAnomalyDetector": LinkAnomalyDetector,
        "BandwidthAuditReconciler": BandwidthAuditReconciler,
        "NocThreatSnapshot": NocThreatSnapshot,
        "NetworkIntelApiDummy": NetworkIntelApiDummy,
        "BandwidthAuditApiDummy": BandwidthAuditApiDummy,
        "NetworkThreatAssessment": NetworkThreatAssessment,
    }
    task_cfgs = {
        "PortScanCollector": PortScanCollector_task_config,
        "RouteTableRecon": RouteTableRecon_task_config,
        "DnsIntelSync": DnsIntelSync_task_config,
        "FlowInterceptor": FlowInterceptor_task_config,
        "DeviceFingerprinter": DeviceFingerprinter_task_config,
        "BandwidthAnalyzer": BandwidthAnalyzer_task_config,
        "LinkAnomalyDetector": LinkAnomalyDetector_task_config,
        "BandwidthAuditReconciler": BandwidthAuditReconciler_task_config,
        "NocThreatSnapshot": NocThreatSnapshot_task_config,
        "NetworkIntelApiDummy": NetworkIntelApiDummy_task_config,
        "BandwidthAuditApiDummy": BandwidthAuditApiDummy_task_config,
        "NetworkThreatAssessment": NetworkThreatAssessment_task_config,
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
