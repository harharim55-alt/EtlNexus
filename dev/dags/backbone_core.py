"""backbone_core — Core network backbone aggregation pipeline.

Builds enriched device profiles, reconciles bandwidth costs, generates ML
link failure predictions, and produces NOC dashboard snapshots. Runs daily at
01:00 UTC with deep dependency chains (depth 5).
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
    DnsRecordSync_task_config,
    BandwidthBillingAggregator_task_config,
    DeviceFingerprintEnrichment_task_config,
    BandwidthCostReconciliation_task_config,
    LinkFailurePrediction_task_config,
    NocDashboardSnapshot_task_config,
    NetworkInsightsApiDummy_task_config,
    BandwidthReportsApiDummy_task_config,
    UnifiedNetworkAssessment_task_config,
)
from hourly.task_configs import NetflowCapture_task_config
from daily.resources import (
    SwitchPortCollector_resources,
    BgpRouteSync_resources,
    DnsRecordSync_resources,
    BandwidthBillingAggregator_resources,
    DeviceFingerprintEnrichment_resources,
    BandwidthCostReconciliation_resources,
    LinkFailurePrediction_resources,
    NocDashboardSnapshot_resources,
    NetworkInsightsApiDummy_resources,
    BandwidthReportsApiDummy_resources,
    UnifiedNetworkAssessment_resources,
)
from hourly.resources import NetflowCapture_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="backbone_core",
    default_args=default_args,
    description="Core network backbone — deep dependency chains",
    schedule="0 1 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
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

        NetflowCapture = PythonOperator(
            task_id="NetflowCapture",
            python_callable=run_etl,
            params={
                "needs": NetflowCapture_task_config.needs,
                "prefers": NetflowCapture_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetflowCapture",
                "resources": NetflowCapture_resources.resources,
            },
        )

    # --- Oasis cross-DAG tasks ---
    with TaskGroup("Oasis-Collection", prefix_group_id=True) as oasis_collection:
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

    # --- Enrichment group (depth 2-3) ---
    with TaskGroup("Dagger-Enrichment", prefix_group_id=True) as enrichment:
        DeviceFingerprintEnrichment = PythonOperator(
            task_id="DeviceFingerprintEnrichment",
            python_callable=run_etl,
            params={
                "needs": DeviceFingerprintEnrichment_task_config.needs,
                "prefers": DeviceFingerprintEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeviceFingerprintEnrichment",
                "resources": DeviceFingerprintEnrichment_resources.resources,
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

        LinkFailurePrediction = PythonOperator(
            task_id="LinkFailurePrediction",
            python_callable=run_etl,
            params={
                "needs": LinkFailurePrediction_task_config.needs,
                "prefers": LinkFailurePrediction_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "LinkFailurePrediction",
                "resources": LinkFailurePrediction_resources.resources,
            },
        )

        BandwidthCostReconciliation = PythonOperator(
            task_id="BandwidthCostReconciliation",
            python_callable=run_etl,
            params={
                "needs": BandwidthCostReconciliation_task_config.needs,
                "prefers": BandwidthCostReconciliation_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthCostReconciliation",
                "resources": BandwidthCostReconciliation_resources.resources,
            },
        )

    # --- Assessment group (depth 3-4) — comprehensive analysis ---
    with TaskGroup("Dagger-Assessment", prefix_group_id=True) as assessment:
        UnifiedNetworkAssessment = PythonOperator(
            task_id="UnifiedNetworkAssessment",
            python_callable=run_etl,
            params={
                "needs": UnifiedNetworkAssessment_task_config.needs,
                "prefers": UnifiedNetworkAssessment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "UnifiedNetworkAssessment",
                "resources": UnifiedNetworkAssessment_resources.resources,
            },
        )

    # --- Delivery group (depth 4) — leaf nodes ---
    with TaskGroup("Dagger-Delivery", prefix_group_id=True) as delivery:
        NocDashboardSnapshot = PythonOperator(
            task_id="NocDashboardSnapshot",
            python_callable=run_etl,
            params={
                "needs": NocDashboardSnapshot_task_config.needs,
                "prefers": NocDashboardSnapshot_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NocDashboardSnapshot",
                "resources": NocDashboardSnapshot_resources.resources,
            },
        )

        NetworkInsightsApiDummy = PythonOperator(
            task_id="NetworkInsightsApiDummy",
            python_callable=run_etl,
            params={
                "needs": NetworkInsightsApiDummy_task_config.needs,
                "prefers": NetworkInsightsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetworkInsightsApiDummy",
                "resources": NetworkInsightsApiDummy_resources.resources,
            },
        )

        BandwidthReportsApiDummy = PythonOperator(
            task_id="BandwidthReportsApiDummy",
            python_callable=run_etl,
            params={
                "needs": BandwidthReportsApiDummy_task_config.needs,
                "prefers": BandwidthReportsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthReportsApiDummy",
                "resources": BandwidthReportsApiDummy_resources.resources,
            },
        )

    # --- Bouncer wiring (bouncers → root ETL tasks) ---
    SwitchTelemetryBouncer >> SwitchPortCollector
    BgpFeedBouncer >> BgpRouteSync
    NetflowCollectorBouncer >> NetflowCapture
    DnsQueryLogBouncer >> DnsRecordSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SwitchPortCollector": SwitchPortCollector,
        "BgpRouteSync": BgpRouteSync,
        "DnsRecordSync": DnsRecordSync,
        "NetflowCapture": NetflowCapture,
        "DeviceFingerprintEnrichment": DeviceFingerprintEnrichment,
        "BandwidthBillingAggregator": BandwidthBillingAggregator,
        "LinkFailurePrediction": LinkFailurePrediction,
        "BandwidthCostReconciliation": BandwidthCostReconciliation,
        "NocDashboardSnapshot": NocDashboardSnapshot,
        "NetworkInsightsApiDummy": NetworkInsightsApiDummy,
        "BandwidthReportsApiDummy": BandwidthReportsApiDummy,
        "UnifiedNetworkAssessment": UnifiedNetworkAssessment,
    }
    task_cfgs = {
        "SwitchPortCollector": SwitchPortCollector_task_config,
        "BgpRouteSync": BgpRouteSync_task_config,
        "DnsRecordSync": DnsRecordSync_task_config,
        "NetflowCapture": NetflowCapture_task_config,
        "DeviceFingerprintEnrichment": DeviceFingerprintEnrichment_task_config,
        "BandwidthBillingAggregator": BandwidthBillingAggregator_task_config,
        "LinkFailurePrediction": LinkFailurePrediction_task_config,
        "BandwidthCostReconciliation": BandwidthCostReconciliation_task_config,
        "NocDashboardSnapshot": NocDashboardSnapshot_task_config,
        "NetworkInsightsApiDummy": NetworkInsightsApiDummy_task_config,
        "BandwidthReportsApiDummy": BandwidthReportsApiDummy_task_config,
        "UnifiedNetworkAssessment": UnifiedNetworkAssessment_task_config,
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
