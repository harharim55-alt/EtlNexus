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
from sensor_runner import run_sensor

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

    # --- Sensors group (data ingestion) ---
    with TaskGroup("Prism-Sensors", prefix_group_id=True) as sensors:
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

    # --- Ingestion group (depth 0-2) — collection and enrichment ---
    with TaskGroup("Prism-Ingestion", prefix_group_id=True) as ingestion:
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

        PacketInspectionEnrichment = PythonOperator(
            task_id="PacketInspectionEnrichment",
            python_callable=run_etl,
            params={
                "etl_name": "PacketInspectionEnrichment",
                "category": "Protocol Analytics",
                "schedule": "Daily at 03:30 UTC",
                "needs": PacketInspectionEnrichment_task_config.needs,
                "prefers": PacketInspectionEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "PacketInspectionEnrichment",
                "needs": PacketInspectionEnrichment_task_config.needs, "prefers": PacketInspectionEnrichment_task_config.prefers,
                "category": "Protocol Analytics",
                "schedule": "Daily at 03:30 UTC",
                "resources": PacketInspectionEnrichment_resources.resources,
            },
        )

    # --- Consumers group (depth 3) — downstream analytics ---
    with TaskGroup("Prism-Consumers", prefix_group_id=True) as consumers:
        ProtocolAdoptionTracker = PythonOperator(
            task_id="ProtocolAdoptionTracker",
            python_callable=run_etl,
            params={
                "etl_name": "ProtocolAdoptionTracker",
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "needs": ProtocolAdoptionTracker_task_config.needs,
                "prefers": ProtocolAdoptionTracker_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ProtocolAdoptionTracker",
                "needs": ProtocolAdoptionTracker_task_config.needs, "prefers": ProtocolAdoptionTracker_task_config.prefers,
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "resources": ProtocolAdoptionTracker_resources.resources,
            },
        )

        HandshakeCompletionAnalysis = PythonOperator(
            task_id="HandshakeCompletionAnalysis",
            python_callable=run_etl,
            params={
                "etl_name": "HandshakeCompletionAnalysis",
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "needs": HandshakeCompletionAnalysis_task_config.needs,
                "prefers": HandshakeCompletionAnalysis_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "HandshakeCompletionAnalysis",
                "needs": HandshakeCompletionAnalysis_task_config.needs, "prefers": HandshakeCompletionAnalysis_task_config.prefers,
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "resources": HandshakeCompletionAnalysis_resources.resources,
            },
        )

        AbRoutingExperimentEngine = PythonOperator(
            task_id="AbRoutingExperimentEngine",
            python_callable=run_etl,
            params={
                "etl_name": "AbRoutingExperimentEngine",
                "category": "Network Science",
                "schedule": "Daily at 04:30 UTC",
                "needs": AbRoutingExperimentEngine_task_config.needs,
                "prefers": AbRoutingExperimentEngine_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "AbRoutingExperimentEngine",
                "needs": AbRoutingExperimentEngine_task_config.needs, "prefers": AbRoutingExperimentEngine_task_config.prefers,
                "category": "Network Science",
                "schedule": "Daily at 04:30 UTC",
                "resources": AbRoutingExperimentEngine_resources.resources,
            },
        )

        EndpointActivityScoring = PythonOperator(
            task_id="EndpointActivityScoring",
            python_callable=run_etl,
            params={
                "etl_name": "EndpointActivityScoring",
                "category": "Predictive Analytics",
                "schedule": "Daily at 04:30 UTC",
                "needs": EndpointActivityScoring_task_config.needs,
                "prefers": EndpointActivityScoring_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "EndpointActivityScoring",
                "needs": EndpointActivityScoring_task_config.needs, "prefers": EndpointActivityScoring_task_config.prefers,
                "category": "Predictive Analytics",
                "schedule": "Daily at 04:30 UTC",
                "resources": EndpointActivityScoring_resources.resources,
            },
        )

        DeviceOnboardingMonitor = PythonOperator(
            task_id="DeviceOnboardingMonitor",
            python_callable=run_etl,
            params={
                "etl_name": "DeviceOnboardingMonitor",
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "needs": DeviceOnboardingMonitor_task_config.needs,
                "prefers": DeviceOnboardingMonitor_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeviceOnboardingMonitor",
                "needs": DeviceOnboardingMonitor_task_config.needs, "prefers": DeviceOnboardingMonitor_task_config.prefers,
                "category": "Protocol Analytics",
                "schedule": "Daily at 04:00 UTC",
                "resources": DeviceOnboardingMonitor_resources.resources,
            },
        )

        TrafficClassSegments = PythonOperator(
            task_id="TrafficClassSegments",
            python_callable=run_etl,
            params={
                "etl_name": "TrafficClassSegments",
                "category": "Protocol Analytics",
                "schedule": "Daily at 05:00 UTC",
                "needs": TrafficClassSegments_task_config.needs,
                "prefers": TrafficClassSegments_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "TrafficClassSegments",
                "needs": TrafficClassSegments_task_config.needs, "prefers": TrafficClassSegments_task_config.prefers,
                "category": "Protocol Analytics",
                "schedule": "Daily at 05:00 UTC",
                "resources": TrafficClassSegments_resources.resources,
            },
        )

        CapacityMetricsApiDummy = PythonOperator(
            task_id="CapacityMetricsApiDummy",
            python_callable=run_etl,
            params={
                "etl_name": "CapacityMetricsApiDummy",
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "needs": CapacityMetricsApiDummy_task_config.needs,
                "prefers": CapacityMetricsApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CapacityMetricsApiDummy",
                "needs": CapacityMetricsApiDummy_task_config.needs, "prefers": CapacityMetricsApiDummy_task_config.prefers,
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "resources": CapacityMetricsApiDummy_resources.resources,
            },
        )

    # --- Sensor wiring (sensors → root ETL tasks) ---
    SwitchTelemetrySensor >> SwitchPortCollector
    NetflowCollectorSensor >> NetflowCapture

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
