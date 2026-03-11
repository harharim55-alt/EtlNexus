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
from sensor_runner import run_sensor

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

    # --- Sensors group (data ingestion) ---
    with TaskGroup("DaggerSensors", prefix_group_id=False) as sensors:
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

        NetflowCollectorSensor = PythonOperator(
            task_id="NetflowCollectorSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "NetflowCollectorSensor",
                "team": "Prism",
                "description": "Captures NetFlow/sFlow records from edge routers",
            },
            op_kwargs={
                "sensor_name": "NetflowCollectorSensor",
                "team": "Prism",
                "description": "Captures NetFlow/sFlow records from edge routers",
                "volume_per_day": 5_200_000,
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

    # --- Collection group (depth 0-1) ---
    with TaskGroup("DaggerCollection", prefix_group_id=False) as collection:
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

        NetflowCapture = PythonOperator(
            task_id="NetflowCapture",
            python_callable=run_etl,
            params={
                "etl_name": "NetflowCapture",
                "category": "Traffic Analytics",
                "schedule": "Every 4 Hours",
                "needs": NetflowCapture_task_config.needs,
                "prefers": NetflowCapture_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetflowCapture",
                "needs": NetflowCapture_task_config.needs, "prefers": NetflowCapture_task_config.prefers,
                "category": "Traffic Analytics",
                "schedule": "Every 4 Hours",
                "resources": NetflowCapture_resources.resources,
            },
        )

    # --- Oasis cross-DAG tasks ---
    with TaskGroup("OasisCollection", prefix_group_id=False) as oasis_collection:
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

    # --- Enrichment group (depth 2-3) ---
    with TaskGroup("DaggerEnrichment", prefix_group_id=False) as enrichment:
        DeviceFingerprintEnrichment = PythonOperator(
            task_id="DeviceFingerprintEnrichment",
            python_callable=run_etl,
            params={
                "etl_name": "DeviceFingerprintEnrichment",
                "category": "Network Infrastructure",
                "schedule": "Daily at 02:00 UTC",
                "needs": DeviceFingerprintEnrichment_task_config.needs,
                "prefers": DeviceFingerprintEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeviceFingerprintEnrichment",
                "needs": DeviceFingerprintEnrichment_task_config.needs, "prefers": DeviceFingerprintEnrichment_task_config.prefers,
                "category": "Network Infrastructure",
                "schedule": "Daily at 02:00 UTC",
                "resources": DeviceFingerprintEnrichment_resources.resources,
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

        LinkFailurePrediction = PythonOperator(
            task_id="LinkFailurePrediction",
            python_callable=run_etl,
            params={
                "etl_name": "LinkFailurePrediction",
                "category": "Predictive Analytics",
                "schedule": "Daily at 05:00 UTC",
                "needs": LinkFailurePrediction_task_config.needs,
                "prefers": LinkFailurePrediction_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "LinkFailurePrediction",
                "needs": LinkFailurePrediction_task_config.needs, "prefers": LinkFailurePrediction_task_config.prefers,
                "category": "Predictive Analytics",
                "schedule": "Daily at 05:00 UTC",
                "resources": LinkFailurePrediction_resources.resources,
            },
        )

        BandwidthCostReconciliation = PythonOperator(
            task_id="BandwidthCostReconciliation",
            python_callable=run_etl,
            params={
                "etl_name": "BandwidthCostReconciliation",
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 04:00 UTC",
                "needs": BandwidthCostReconciliation_task_config.needs,
                "prefers": BandwidthCostReconciliation_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthCostReconciliation",
                "needs": BandwidthCostReconciliation_task_config.needs, "prefers": BandwidthCostReconciliation_task_config.prefers,
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 04:00 UTC",
                "resources": BandwidthCostReconciliation_resources.resources,
            },
        )

    # --- Delivery group (depth 4) — leaf nodes ---
    with TaskGroup("DaggerDelivery", prefix_group_id=False) as delivery:
        NocDashboardSnapshot = PythonOperator(
            task_id="NocDashboardSnapshot",
            python_callable=run_etl,
            params={
                "etl_name": "NocDashboardSnapshot",
                "category": "NOC Management",
                "schedule": "Daily at 06:00 UTC",
                "needs": NocDashboardSnapshot_task_config.needs,
                "prefers": NocDashboardSnapshot_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NocDashboardSnapshot",
                "needs": NocDashboardSnapshot_task_config.needs, "prefers": NocDashboardSnapshot_task_config.prefers,
                "category": "NOC Management",
                "schedule": "Daily at 06:00 UTC",
                "resources": NocDashboardSnapshot_resources.resources,
            },
        )

        NetworkInsightsApiDummy = PythonOperator(
            task_id="NetworkInsightsApiDummy",
            python_callable=run_etl,
            params={
                "etl_name": "NetworkInsightsApiDummy",
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "needs": NetworkInsightsApiDummy_task_config.needs,
                "prefers": NetworkInsightsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "NetworkInsightsApiDummy",
                "needs": NetworkInsightsApiDummy_task_config.needs, "prefers": NetworkInsightsApiDummy_task_config.prefers,
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "resources": NetworkInsightsApiDummy_resources.resources,
            },
        )

        BandwidthReportsApiDummy = PythonOperator(
            task_id="BandwidthReportsApiDummy",
            python_callable=run_etl,
            params={
                "etl_name": "BandwidthReportsApiDummy",
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "needs": BandwidthReportsApiDummy_task_config.needs,
                "prefers": BandwidthReportsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "BandwidthReportsApiDummy",
                "needs": BandwidthReportsApiDummy_task_config.needs, "prefers": BandwidthReportsApiDummy_task_config.prefers,
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "resources": BandwidthReportsApiDummy_resources.resources,
            },
        )

    # --- Sensor wiring (sensors → root ETL tasks) ---
    SwitchTelemetrySensor >> SwitchPortCollector
    BgpFeedSensor >> BgpRouteSync
    NetflowCollectorSensor >> NetflowCapture
    DnsQueryLogSensor >> DnsRecordSync

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
