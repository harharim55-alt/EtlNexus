"""application_mesh — Application layer service mesh analytics pipeline.

Enriches raw network flows with device context, then fans out to seven
downstream ETLs: protocol adoption tracking, handshake completion analysis,
A/B routing experiments, endpoint activity scoring, device onboarding
monitoring, traffic classification, and a capacity metrics API layer.
Runs daily at 03:30 UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

from daily.task_configs import (
    SwitchPortCollector_task_config,
    PacketInspectionEnrichment_task_config,
    ProtocolAdoptionTracker_task_config,
    HandshakeCompletionAnalysis_task_config,
    AbRoutingExperimentEngine_task_config,
    EndpointActivityScoring_task_config,
    DeviceOnboardingMonitor_task_config,
    TrafficClassSegments_task_config,
    CapacityMetricsApiDummy_task_config,
)
from hourly.task_configs import NetflowCapture_task_config
from daily.resources import (
    SwitchPortCollector_resources,
    PacketInspectionEnrichment_resources,
    ProtocolAdoptionTracker_resources,
    HandshakeCompletionAnalysis_resources,
    AbRoutingExperimentEngine_resources,
    EndpointActivityScoring_resources,
    DeviceOnboardingMonitor_resources,
    TrafficClassSegments_resources,
    CapacityMetricsApiDummy_resources,
)
from hourly.resources import NetflowCapture_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="application_mesh",
    default_args=default_args,
    description="Application layer service mesh — protocol adoption, handshakes, experiments, endpoint scoring",
    schedule="30 3 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    # --- Bouncers group (data ingestion) ---
    with TaskGroup("Prism-Bouncers", prefix_group_id=True) as bouncers:
        SwitchTelemetryBouncer = PythonOperator(
            task_id="SwitchTelemetryBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SwitchTelemetryBouncer",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
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

    # --- Ingestion group (depth 0-2) — collection and enrichment ---
    with TaskGroup("Prism-Ingestion", prefix_group_id=True) as ingestion:
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

        PacketInspectionEnrichment = PythonOperator(
            task_id="PacketInspectionEnrichment",
            python_callable=run_etl,
            params={
                "needs": PacketInspectionEnrichment_task_config.needs,
                "prefers": PacketInspectionEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "PacketInspectionEnrichment",
                "resources": PacketInspectionEnrichment_resources.resources,
            },
        )

    # --- Consumers group (depth 3) — downstream analytics ---
    with TaskGroup("Prism-Consumers", prefix_group_id=True) as consumers:
        ProtocolAdoptionTracker = PythonOperator(
            task_id="ProtocolAdoptionTracker",
            python_callable=run_etl,
            params={
                "needs": ProtocolAdoptionTracker_task_config.needs,
                "prefers": ProtocolAdoptionTracker_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ProtocolAdoptionTracker",
                "resources": ProtocolAdoptionTracker_resources.resources,
            },
        )

        HandshakeCompletionAnalysis = PythonOperator(
            task_id="HandshakeCompletionAnalysis",
            python_callable=run_etl,
            params={
                "needs": HandshakeCompletionAnalysis_task_config.needs,
                "prefers": HandshakeCompletionAnalysis_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "HandshakeCompletionAnalysis",
                "resources": HandshakeCompletionAnalysis_resources.resources,
            },
        )

        AbRoutingExperimentEngine = PythonOperator(
            task_id="AbRoutingExperimentEngine",
            python_callable=run_etl,
            params={
                "needs": AbRoutingExperimentEngine_task_config.needs,
                "prefers": AbRoutingExperimentEngine_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "AbRoutingExperimentEngine",
                "resources": AbRoutingExperimentEngine_resources.resources,
            },
        )

        EndpointActivityScoring = PythonOperator(
            task_id="EndpointActivityScoring",
            python_callable=run_etl,
            params={
                "needs": EndpointActivityScoring_task_config.needs,
                "prefers": EndpointActivityScoring_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "EndpointActivityScoring",
                "resources": EndpointActivityScoring_resources.resources,
            },
        )

        DeviceOnboardingMonitor = PythonOperator(
            task_id="DeviceOnboardingMonitor",
            python_callable=run_etl,
            params={
                "needs": DeviceOnboardingMonitor_task_config.needs,
                "prefers": DeviceOnboardingMonitor_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeviceOnboardingMonitor",
                "resources": DeviceOnboardingMonitor_resources.resources,
            },
        )

        TrafficClassSegments = PythonOperator(
            task_id="TrafficClassSegments",
            python_callable=run_etl,
            params={
                "needs": TrafficClassSegments_task_config.needs,
                "prefers": TrafficClassSegments_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "TrafficClassSegments",
                "resources": TrafficClassSegments_resources.resources,
            },
        )

        CapacityMetricsApiDummy = PythonOperator(
            task_id="CapacityMetricsApiDummy",
            python_callable=run_etl,
            params={
                "needs": CapacityMetricsApiDummy_task_config.needs,
                "prefers": CapacityMetricsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CapacityMetricsApiDummy",
                "resources": CapacityMetricsApiDummy_resources.resources,
            },
        )

    # --- Bouncer wiring (bouncers → root ETL tasks) ---
    SwitchTelemetryBouncer >> SwitchPortCollector
    NetflowCollectorBouncer >> NetflowCapture

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SwitchPortCollector": SwitchPortCollector,
        "NetflowCapture": NetflowCapture,
        "PacketInspectionEnrichment": PacketInspectionEnrichment,
        "ProtocolAdoptionTracker": ProtocolAdoptionTracker,
        "HandshakeCompletionAnalysis": HandshakeCompletionAnalysis,
        "AbRoutingExperimentEngine": AbRoutingExperimentEngine,
        "EndpointActivityScoring": EndpointActivityScoring,
        "DeviceOnboardingMonitor": DeviceOnboardingMonitor,
        "TrafficClassSegments": TrafficClassSegments,
        "CapacityMetricsApiDummy": CapacityMetricsApiDummy,
    }
    task_cfgs = {
        "SwitchPortCollector": SwitchPortCollector_task_config,
        "NetflowCapture": NetflowCapture_task_config,
        "PacketInspectionEnrichment": PacketInspectionEnrichment_task_config,
        "ProtocolAdoptionTracker": ProtocolAdoptionTracker_task_config,
        "HandshakeCompletionAnalysis": HandshakeCompletionAnalysis_task_config,
        "AbRoutingExperimentEngine": AbRoutingExperimentEngine_task_config,
        "EndpointActivityScoring": EndpointActivityScoring_task_config,
        "DeviceOnboardingMonitor": DeviceOnboardingMonitor_task_config,
        "TrafficClassSegments": TrafficClassSegments_task_config,
        "CapacityMetricsApiDummy": CapacityMetricsApiDummy_task_config,
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
