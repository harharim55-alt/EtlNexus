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

from etl_runner import run_etl

from daily.task_configs import (
    switch_port_collector_task_config,
    packet_inspection_enrichment_task_config,
    protocol_adoption_tracker_task_config,
    handshake_completion_analysis_task_config,
    ab_routing_experiment_engine_task_config,
    endpoint_activity_scoring_task_config,
    device_onboarding_monitor_task_config,
    traffic_class_segments_task_config,
    capacity_metrics_api_task_config,
)
from hourly.task_configs import netflow_capture_task_config
from daily.resources import (
    switch_port_collector_resources,
    packet_inspection_enrichment_resources,
    protocol_adoption_tracker_resources,
    handshake_completion_analysis_resources,
    ab_routing_experiment_engine_resources,
    endpoint_activity_scoring_resources,
    device_onboarding_monitor_resources,
    traffic_class_segments_resources,
    capacity_metrics_api_resources,
)
from hourly.resources import netflow_capture_resources

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

    # --- Root layer (depth 0) ---
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

    # --- Layer 1 (depth 1) ---
    netflow_capture = PythonOperator(
        task_id="netflow_capture",
        python_callable=run_etl,
        params={
            "etl_name": "netflow_capture",
            "category": "Traffic Analytics",
            "schedule": "Every 4 Hours",
            "needs": ["switch_port_collector"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "netflow_capture",
            "needs": ["switch_port_collector"], "prefers": [],
            "category": "Traffic Analytics",
            "schedule": "Every 4 Hours",
            "resources": netflow_capture_resources.resources,
        },
    )

    # --- Layer 2 (depth 2) — upstream hub ---
    packet_inspection_enrichment = PythonOperator(
        task_id="packet_inspection_enrichment",
        python_callable=run_etl,
        params={
            "etl_name": "packet_inspection_enrichment",
            "category": "Protocol Analytics",
            "schedule": "Daily at 03:30 UTC",
            "needs": ["netflow_capture", "switch_port_collector"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "packet_inspection_enrichment",
            "needs": ["netflow_capture", "switch_port_collector"], "prefers": [],
            "category": "Protocol Analytics",
            "schedule": "Daily at 03:30 UTC",
            "resources": packet_inspection_enrichment_resources.resources,
        },
    )

    # --- Layer 3 (depth 3) — downstream consumers ---
    protocol_adoption_tracker = PythonOperator(
        task_id="protocol_adoption_tracker",
        python_callable=run_etl,
        params={
            "etl_name": "protocol_adoption_tracker",
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "protocol_adoption_tracker",
            "needs": ["packet_inspection_enrichment"], "prefers": [],
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "resources": protocol_adoption_tracker_resources.resources,
        },
    )

    handshake_completion_analysis = PythonOperator(
        task_id="handshake_completion_analysis",
        python_callable=run_etl,
        params={
            "etl_name": "handshake_completion_analysis",
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "handshake_completion_analysis",
            "needs": ["packet_inspection_enrichment"], "prefers": [],
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "resources": handshake_completion_analysis_resources.resources,
        },
    )

    ab_routing_experiment_engine = PythonOperator(
        task_id="ab_routing_experiment_engine",
        python_callable=run_etl,
        params={
            "etl_name": "ab_routing_experiment_engine",
            "category": "Network Science",
            "schedule": "Daily at 04:30 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": ["protocol_adoption_tracker"],
        },
        op_kwargs={
            "etl_name": "ab_routing_experiment_engine",
            "needs": ["packet_inspection_enrichment"], "prefers": ["protocol_adoption_tracker"],
            "category": "Network Science",
            "schedule": "Daily at 04:30 UTC",
            "resources": ab_routing_experiment_engine_resources.resources,
        },
    )

    endpoint_activity_scoring = PythonOperator(
        task_id="endpoint_activity_scoring",
        python_callable=run_etl,
        params={
            "etl_name": "endpoint_activity_scoring",
            "category": "Predictive Analytics",
            "schedule": "Daily at 04:30 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": ["device_fingerprint_enrichment"],
        },
        op_kwargs={
            "etl_name": "endpoint_activity_scoring",
            "needs": ["packet_inspection_enrichment"], "prefers": ["device_fingerprint_enrichment"],
            "category": "Predictive Analytics",
            "schedule": "Daily at 04:30 UTC",
            "resources": endpoint_activity_scoring_resources.resources,
        },
    )

    device_onboarding_monitor = PythonOperator(
        task_id="device_onboarding_monitor",
        python_callable=run_etl,
        params={
            "etl_name": "device_onboarding_monitor",
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": [],
        },
        op_kwargs={
            "etl_name": "device_onboarding_monitor",
            "needs": ["packet_inspection_enrichment"], "prefers": [],
            "category": "Protocol Analytics",
            "schedule": "Daily at 04:00 UTC",
            "resources": device_onboarding_monitor_resources.resources,
        },
    )

    traffic_class_segments = PythonOperator(
        task_id="traffic_class_segments",
        python_callable=run_etl,
        params={
            "etl_name": "traffic_class_segments",
            "category": "Protocol Analytics",
            "schedule": "Daily at 05:00 UTC",
            "needs": ["packet_inspection_enrichment"],
            "prefers": ["endpoint_activity_scoring"],
        },
        op_kwargs={
            "etl_name": "traffic_class_segments",
            "needs": ["packet_inspection_enrichment"], "prefers": ["endpoint_activity_scoring"],
            "category": "Protocol Analytics",
            "schedule": "Daily at 05:00 UTC",
            "resources": traffic_class_segments_resources.resources,
        },
    )

    capacity_metrics_api = PythonOperator(
        task_id="capacity_metrics_api",
        python_callable=run_etl,
        params={
            "etl_name": "capacity_metrics_api",
            "category": "Network APIs",
            "schedule": "On-demand (API)",
            "needs": ["packet_inspection_enrichment"],
            "prefers": ["protocol_adoption_tracker", "endpoint_activity_scoring"],
        },
        op_kwargs={
            "etl_name": "capacity_metrics_api",
            "needs": ["packet_inspection_enrichment"], "prefers": ["protocol_adoption_tracker", "endpoint_activity_scoring"],
            "category": "Network APIs",
            "schedule": "On-demand (API)",
            "resources": capacity_metrics_api_resources.resources,
        },
    )

    # --- Dependency wiring ---
    switch_port_collector >> netflow_capture
    netflow_capture >> packet_inspection_enrichment
    switch_port_collector >> packet_inspection_enrichment
    packet_inspection_enrichment >> protocol_adoption_tracker
    packet_inspection_enrichment >> handshake_completion_analysis
    packet_inspection_enrichment >> ab_routing_experiment_engine
    packet_inspection_enrichment >> endpoint_activity_scoring
    packet_inspection_enrichment >> device_onboarding_monitor
    packet_inspection_enrichment >> traffic_class_segments
    packet_inspection_enrichment >> capacity_metrics_api
