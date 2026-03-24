"""traffic_analysis — Deep traffic analysis — packet inspection, protocol analysis, endpoint risk scoring.

Enriches raw network flows with device context, then fans out to seven
downstream ETLs: protocol analysis, handshake analysis,
routing experiments, endpoint risk scoring, provisioning auditing,
traffic classification, and a capacity intel API layer.
Runs daily at 03:30 UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

from daily.task_configs import (
    PortScanCollector_task_config,
    DeepPacketInspector_task_config,
    ProtocolAnalyzer_task_config,
    HandshakeAnalyzer_task_config,
    RoutingExperimentEngine_task_config,
    EndpointRiskScorer_task_config,
    ProvisioningAuditor_task_config,
    TrafficClassifier_task_config,
    CapacityIntelApiDummy_task_config,
)
from hourly.task_configs import FlowInterceptor_task_config
from daily.resources import (
    PortScanCollector_resources,
    DeepPacketInspector_resources,
    ProtocolAnalyzer_resources,
    HandshakeAnalyzer_resources,
    RoutingExperimentEngine_resources,
    EndpointRiskScorer_resources,
    ProvisioningAuditor_resources,
    TrafficClassifier_resources,
    CapacityIntelApiDummy_resources,
)
from hourly.resources import FlowInterceptor_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="traffic_analysis",
    default_args=default_args,
    description="Deep traffic analysis — packet inspection, protocol analysis, endpoint risk scoring",
    schedule="30 3 * * *",
    start_date=datetime(2026, 3, 8),
    catchup=True,
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

        DeepPacketInspector = PythonOperator(
            task_id="DeepPacketInspector",
            python_callable=run_etl,
            params={
                "needs": DeepPacketInspector_task_config.needs,
                "prefers": DeepPacketInspector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DeepPacketInspector",
                "resources": DeepPacketInspector_resources.resources,
            },
        )

    # --- Consumers group (depth 3) — downstream analytics ---
    with TaskGroup("Prism-Consumers", prefix_group_id=True) as consumers:
        ProtocolAnalyzer = PythonOperator(
            task_id="ProtocolAnalyzer",
            python_callable=run_etl,
            params={
                "needs": ProtocolAnalyzer_task_config.needs,
                "prefers": ProtocolAnalyzer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ProtocolAnalyzer",
                "resources": ProtocolAnalyzer_resources.resources,
            },
        )

        HandshakeAnalyzer = PythonOperator(
            task_id="HandshakeAnalyzer",
            python_callable=run_etl,
            params={
                "needs": HandshakeAnalyzer_task_config.needs,
                "prefers": HandshakeAnalyzer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "HandshakeAnalyzer",
                "resources": HandshakeAnalyzer_resources.resources,
            },
        )

        RoutingExperimentEngine = PythonOperator(
            task_id="RoutingExperimentEngine",
            python_callable=run_etl,
            params={
                "needs": RoutingExperimentEngine_task_config.needs,
                "prefers": RoutingExperimentEngine_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "RoutingExperimentEngine",
                "resources": RoutingExperimentEngine_resources.resources,
            },
        )

        EndpointRiskScorer = PythonOperator(
            task_id="EndpointRiskScorer",
            python_callable=run_etl,
            params={
                "needs": EndpointRiskScorer_task_config.needs,
                "prefers": EndpointRiskScorer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "EndpointRiskScorer",
                "resources": EndpointRiskScorer_resources.resources,
            },
        )

        ProvisioningAuditor = PythonOperator(
            task_id="ProvisioningAuditor",
            python_callable=run_etl,
            params={
                "needs": ProvisioningAuditor_task_config.needs,
                "prefers": ProvisioningAuditor_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ProvisioningAuditor",
                "resources": ProvisioningAuditor_resources.resources,
            },
        )

        TrafficClassifier = PythonOperator(
            task_id="TrafficClassifier",
            python_callable=run_etl,
            params={
                "needs": TrafficClassifier_task_config.needs,
                "prefers": TrafficClassifier_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "TrafficClassifier",
                "resources": TrafficClassifier_resources.resources,
            },
        )

        CapacityIntelApiDummy = PythonOperator(
            task_id="CapacityIntelApiDummy",
            python_callable=run_etl,
            params={
                "needs": CapacityIntelApiDummy_task_config.needs,
                "prefers": CapacityIntelApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CapacityIntelApiDummy",
                "resources": CapacityIntelApiDummy_resources.resources,
            },
        )

    # --- Bouncer wiring (bouncers → root ETL tasks) ---
    SwitchTelemetryBouncer >> PortScanCollector
    NetflowCollectorBouncer >> FlowInterceptor

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "PortScanCollector": PortScanCollector,
        "FlowInterceptor": FlowInterceptor,
        "DeepPacketInspector": DeepPacketInspector,
        "ProtocolAnalyzer": ProtocolAnalyzer,
        "HandshakeAnalyzer": HandshakeAnalyzer,
        "RoutingExperimentEngine": RoutingExperimentEngine,
        "EndpointRiskScorer": EndpointRiskScorer,
        "ProvisioningAuditor": ProvisioningAuditor,
        "TrafficClassifier": TrafficClassifier,
        "CapacityIntelApiDummy": CapacityIntelApiDummy,
    }
    task_cfgs = {
        "PortScanCollector": PortScanCollector_task_config,
        "FlowInterceptor": FlowInterceptor_task_config,
        "DeepPacketInspector": DeepPacketInspector_task_config,
        "ProtocolAnalyzer": ProtocolAnalyzer_task_config,
        "HandshakeAnalyzer": HandshakeAnalyzer_task_config,
        "RoutingExperimentEngine": RoutingExperimentEngine_task_config,
        "EndpointRiskScorer": EndpointRiskScorer_task_config,
        "ProvisioningAuditor": ProvisioningAuditor_task_config,
        "TrafficClassifier": TrafficClassifier_task_config,
        "CapacityIntelApiDummy": CapacityIntelApiDummy_task_config,
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
