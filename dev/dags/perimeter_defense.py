"""perimeter_defense — Network security perimeter pipeline with real-world failure scenarios.

Demonstrates mixed success/failure states: a flaky DHCP server source that
fails, resilient downstream ETLs that tolerate soft-dependency failures via
trigger_rule="all_done", and hard-dependency failures that cascade through
the pipeline. Runs daily at 02:00 UTC.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_sensor

from daily.task_configs import (
    dhcp_lease_sync_task_config,
    http_access_log_ingest_task_config,
    traffic_attribution_model_task_config,
    threat_scoring_pipeline_task_config,
    peering_roi_calculator_task_config,
    capacity_planning_forecast_task_config,
    mac_address_enrichment_task_config,
    weekly_network_digest_task_config,
    cdn_cost_reconciler_task_config,
)
from daily.resources import (
    dhcp_lease_sync_resources,
    http_access_log_ingest_resources,
    traffic_attribution_model_resources,
    threat_scoring_pipeline_resources,
    peering_roi_calculator_resources,
    capacity_planning_forecast_resources,
    mac_address_enrichment_resources,
    weekly_network_digest_resources,
    cdn_cost_reconciler_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="perimeter_defense",
    default_args=default_args,
    description="Network security perimeter — real-world failure scenarios with mixed success/failure states",
    schedule="0 2 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    # --- Sensors group (data ingestion) ---
    with TaskGroup("sensors", prefix_group_id=False) as sensors:
        syslog_receiver_sensor = PythonOperator(
            task_id="syslog_receiver_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "syslog_receiver_sensor",
                "team": "Security Engineering",
                "description": "Receives syslog messages from network devices and firewalls",
            },
            op_kwargs={
                "sensor_name": "syslog_receiver_sensor",
                "team": "Security Engineering",
                "description": "Receives syslog messages from network devices and firewalls",
                "volume_per_day": 8_500_000,
            },
        )

        firewall_event_sensor = PythonOperator(
            task_id="firewall_event_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "firewall_event_sensor",
                "team": "Security Engineering",
                "description": "Captures firewall rule hit events and connection logs",
            },
            op_kwargs={
                "sensor_name": "firewall_event_sensor",
                "team": "Security Engineering",
                "description": "Captures firewall rule hit events and connection logs",
                "volume_per_day": 3_100_000,
            },
        )

        http_access_log_sensor = PythonOperator(
            task_id="http_access_log_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "http_access_log_sensor",
                "team": "NOC Operations",
                "description": "Ingests HTTP proxy and CDN access logs",
            },
            op_kwargs={
                "sensor_name": "http_access_log_sensor",
                "team": "NOC Operations",
                "description": "Ingests HTTP proxy and CDN access logs",
                "volume_per_day": 18_000_000,
            },
        )

    # --- Sources group (depth 0) — two independent sources ---
    with TaskGroup("sources", prefix_group_id=False) as sources:
        # SCENARIO 1: Flaky source — fails with RuntimeError (simulates DHCP server timeout)
        dhcp_lease_sync = PythonOperator(
            task_id="dhcp_lease_sync",
            python_callable=run_etl,
            params={
                "etl_name": "dhcp_lease_sync",
                "category": "Address Management",
                "schedule": "Daily at 02:00 UTC",
                "needs": [],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "dhcp_lease_sync",
                "needs": [], "prefers": [],
                "category": "Address Management",
                "schedule": "Daily at 02:00 UTC",
                "task_group": "sources",
                "resources": dhcp_lease_sync_resources.resources,
                "simulate_failure": "DHCP server timeout after 30s — lease pool exhausted (429 Too Many Requests)",
            },
        )

        # SCENARIO 2: Reliable source — always succeeds
        http_access_log_ingest = PythonOperator(
            task_id="http_access_log_ingest",
            python_callable=run_etl,
            params={
                "etl_name": "http_access_log_ingest",
                "category": "Traffic Analytics",
                "schedule": "Daily at 02:00 UTC",
                "needs": [],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "http_access_log_ingest",
                "needs": [], "prefers": [],
                "category": "Traffic Analytics",
                "schedule": "Daily at 02:00 UTC",
                "task_group": "sources",
                "resources": http_access_log_ingest_resources.resources,
            },
        )

    # --- Analysis group (depth 1) ---
    with TaskGroup("analysis", prefix_group_id=False) as analysis:
        # SCENARIO 3: Prefers failed, needs succeeded → still works
        # Uses trigger_rule="all_done" to tolerate dhcp_lease_sync failure
        traffic_attribution_model = PythonOperator(
            task_id="traffic_attribution_model",
            python_callable=run_etl,
            trigger_rule="all_done",
            params={
                "etl_name": "traffic_attribution_model",
                "category": "Traffic Engineering",
                "schedule": "Daily at 02:30 UTC",
                "needs": ["http_access_log_ingest"],
                "prefers": ["dhcp_lease_sync"],
            },
            op_kwargs={
                "etl_name": "traffic_attribution_model",
                "needs": ["http_access_log_ingest"], "prefers": ["dhcp_lease_sync"],
                "category": "Traffic Engineering",
                "schedule": "Daily at 02:30 UTC",
                "task_group": "analysis",
                "resources": traffic_attribution_model_resources.resources,
            },
        )

        # SCENARIO 4: Need failed → cascading upstream_failed
        threat_scoring_pipeline = PythonOperator(
            task_id="threat_scoring_pipeline",
            python_callable=run_etl,
            params={
                "etl_name": "threat_scoring_pipeline",
                "category": "Predictive Analytics",
                "schedule": "Daily at 02:30 UTC",
                "needs": ["dhcp_lease_sync"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "threat_scoring_pipeline",
                "needs": ["dhcp_lease_sync"], "prefers": [],
                "category": "Predictive Analytics",
                "schedule": "Daily at 02:30 UTC",
                "task_group": "analysis",
                "resources": threat_scoring_pipeline_resources.resources,
            },
        )

        # SCENARIO 7: Both needs failed (dhcp + http needed) → upstream_failed
        mac_address_enrichment = PythonOperator(
            task_id="mac_address_enrichment",
            python_callable=run_etl,
            params={
                "etl_name": "mac_address_enrichment",
                "category": "Address Management",
                "schedule": "Daily at 02:30 UTC",
                "needs": ["dhcp_lease_sync", "http_access_log_ingest"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "mac_address_enrichment",
                "needs": ["dhcp_lease_sync", "http_access_log_ingest"], "prefers": [],
                "category": "Address Management",
                "schedule": "Daily at 02:30 UTC",
                "task_group": "analysis",
                "resources": mac_address_enrichment_resources.resources,
            },
        )

        # SCENARIO 9: Intermittent — succeeds some runs, fails others (~40% failure rate)
        # Simulates a flaky CDN provider billing API
        cdn_cost_reconciler = PythonOperator(
            task_id="cdn_cost_reconciler",
            python_callable=run_etl,
            params={
                "etl_name": "cdn_cost_reconciler",
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 02:30 UTC",
                "needs": ["http_access_log_ingest"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "cdn_cost_reconciler",
                "needs": ["http_access_log_ingest"], "prefers": [],
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 02:30 UTC",
                "task_group": "analysis",
                "resources": cdn_cost_reconciler_resources.resources,
                "simulate_flaky": "CDN provider billing API — intermittent 503 Service Unavailable",
            },
        )

    # --- Output group (depth 2-3) ---
    with TaskGroup("output", prefix_group_id=False) as output:
        # SCENARIO 5: All needs succeeded → normal happy path
        peering_roi_calculator = PythonOperator(
            task_id="peering_roi_calculator",
            python_callable=run_etl,
            params={
                "etl_name": "peering_roi_calculator",
                "category": "Traffic Engineering",
                "schedule": "Daily at 03:00 UTC",
                "needs": ["traffic_attribution_model"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "peering_roi_calculator",
                "needs": ["traffic_attribution_model"], "prefers": [],
                "category": "Traffic Engineering",
                "schedule": "Daily at 03:00 UTC",
                "task_group": "output",
                "resources": peering_roi_calculator_resources.resources,
            },
        )

        # SCENARIO 6: One of two needs failed → upstream_failed
        capacity_planning_forecast = PythonOperator(
            task_id="capacity_planning_forecast",
            python_callable=run_etl,
            params={
                "etl_name": "capacity_planning_forecast",
                "category": "Predictive Analytics",
                "schedule": "Daily at 03:00 UTC",
                "needs": ["threat_scoring_pipeline", "traffic_attribution_model"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "capacity_planning_forecast",
                "needs": ["threat_scoring_pipeline", "traffic_attribution_model"], "prefers": [],
                "category": "Predictive Analytics",
                "schedule": "Daily at 03:00 UTC",
                "task_group": "output",
                "resources": capacity_planning_forecast_resources.resources,
            },
        )

        # SCENARIO 8: Needs ok, multiple prefers failed → still works
        # Uses trigger_rule="all_done" to tolerate capacity_planning and mac_address failures
        weekly_network_digest = PythonOperator(
            task_id="weekly_network_digest",
            python_callable=run_etl,
            trigger_rule="all_done",
            params={
                "etl_name": "weekly_network_digest",
                "category": "NOC Management",
                "schedule": "Daily at 03:30 UTC",
                "needs": ["peering_roi_calculator"],
                "prefers": ["capacity_planning_forecast", "mac_address_enrichment", "cdn_cost_reconciler"],
            },
            op_kwargs={
                "etl_name": "weekly_network_digest",
                "needs": ["peering_roi_calculator"], "prefers": ["capacity_planning_forecast", "mac_address_enrichment", "cdn_cost_reconciler"],
                "category": "NOC Management",
                "schedule": "Daily at 03:30 UTC",
                "task_group": "output",
                "resources": weekly_network_digest_resources.resources,
            },
        )

    # --- Sensor wiring (sensors → root ETL tasks) ---
    firewall_event_sensor >> dhcp_lease_sync
    syslog_receiver_sensor >> dhcp_lease_sync
    http_access_log_sensor >> http_access_log_ingest

    # --- Dependency wiring ---
    dhcp_lease_sync >> traffic_attribution_model
    http_access_log_ingest >> traffic_attribution_model
    dhcp_lease_sync >> threat_scoring_pipeline
    dhcp_lease_sync >> mac_address_enrichment
    http_access_log_ingest >> mac_address_enrichment
    traffic_attribution_model >> peering_roi_calculator
    threat_scoring_pipeline >> capacity_planning_forecast
    traffic_attribution_model >> capacity_planning_forecast
    http_access_log_ingest >> cdn_cost_reconciler
    peering_roi_calculator >> weekly_network_digest
    capacity_planning_forecast >> weekly_network_digest
    mac_address_enrichment >> weekly_network_digest
    cdn_cost_reconciler >> weekly_network_digest
