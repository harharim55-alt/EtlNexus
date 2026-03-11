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
    switch_port_collector_task_config,
    bgp_route_sync_task_config,
    dns_record_sync_task_config,
    bandwidth_billing_aggregator_task_config,
    device_fingerprint_enrichment_task_config,
    bandwidth_cost_reconciliation_task_config,
    link_failure_prediction_task_config,
    noc_dashboard_snapshot_task_config,
    network_insights_api_task_config,
    bandwidth_reports_api_task_config,
)
from hourly.task_configs import netflow_capture_task_config
from daily.resources import (
    switch_port_collector_resources,
    bgp_route_sync_resources,
    dns_record_sync_resources,
    bandwidth_billing_aggregator_resources,
    device_fingerprint_enrichment_resources,
    bandwidth_cost_reconciliation_resources,
    link_failure_prediction_resources,
    noc_dashboard_snapshot_resources,
    network_insights_api_resources,
    bandwidth_reports_api_resources,
)
from hourly.resources import netflow_capture_resources

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
    with TaskGroup("sensors", prefix_group_id=False) as sensors:
        switch_telemetry_sensor = PythonOperator(
            task_id="switch_telemetry_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "switch_telemetry_sensor",
                "team": "Infrastructure Ops",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
            },
            op_kwargs={
                "sensor_name": "switch_telemetry_sensor",
                "team": "Infrastructure Ops",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
                "volume_per_day": 2_400_000,
            },
        )

        bgp_feed_sensor = PythonOperator(
            task_id="bgp_feed_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "bgp_feed_sensor",
                "team": "Infrastructure Ops",
                "description": "Ingests BGP route announcements from peering routers",
            },
            op_kwargs={
                "sensor_name": "bgp_feed_sensor",
                "team": "Infrastructure Ops",
                "description": "Ingests BGP route announcements from peering routers",
                "volume_per_day": 850_000,
            },
        )

        netflow_collector_sensor = PythonOperator(
            task_id="netflow_collector_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "netflow_collector_sensor",
                "team": "Network Monitoring",
                "description": "Captures NetFlow/sFlow records from edge routers",
            },
            op_kwargs={
                "sensor_name": "netflow_collector_sensor",
                "team": "Network Monitoring",
                "description": "Captures NetFlow/sFlow records from edge routers",
                "volume_per_day": 5_200_000,
            },
        )

        dns_query_log_sensor = PythonOperator(
            task_id="dns_query_log_sensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "dns_query_log_sensor",
                "team": "Network Monitoring",
                "description": "Taps DNS resolver query logs for resolution analytics",
            },
            op_kwargs={
                "sensor_name": "dns_query_log_sensor",
                "team": "Network Monitoring",
                "description": "Taps DNS resolver query logs for resolution analytics",
                "volume_per_day": 12_000_000,
            },
        )

    # --- Collection group (depth 0-1) ---
    with TaskGroup("collection", prefix_group_id=False) as collection:
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
                "task_group": "collection",
                "resources": switch_port_collector_resources.resources,
            },
        )

        bgp_route_sync = PythonOperator(
            task_id="bgp_route_sync",
            python_callable=run_etl,
            params={
                "etl_name": "bgp_route_sync",
                "category": "Transit/Peering",
                "schedule": "Daily at 00:00 UTC",
                "needs": ["switch_port_collector"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "bgp_route_sync",
                "needs": ["switch_port_collector"], "prefers": [],
                "category": "Transit/Peering",
                "schedule": "Daily at 00:00 UTC",
                "task_group": "collection",
                "resources": bgp_route_sync_resources.resources,
            },
        )

        dns_record_sync = PythonOperator(
            task_id="dns_record_sync",
            python_callable=run_etl,
            params={
                "etl_name": "dns_record_sync",
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "needs": [],
                "prefers": ["switch_port_collector"],
            },
            op_kwargs={
                "etl_name": "dns_record_sync",
                "needs": [], "prefers": ["switch_port_collector"],
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "task_group": "collection",
                "resources": dns_record_sync_resources.resources,
            },
        )

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
                "task_group": "collection",
                "resources": netflow_capture_resources.resources,
            },
        )

    # --- Enrichment group (depth 2-3) ---
    with TaskGroup("enrichment", prefix_group_id=False) as enrichment:
        device_fingerprint_enrichment = PythonOperator(
            task_id="device_fingerprint_enrichment",
            python_callable=run_etl,
            params={
                "etl_name": "device_fingerprint_enrichment",
                "category": "Network Infrastructure",
                "schedule": "Daily at 02:00 UTC",
                "needs": ["switch_port_collector", "bgp_route_sync"],
                "prefers": ["dns_record_sync"],
            },
            op_kwargs={
                "etl_name": "device_fingerprint_enrichment",
                "needs": ["switch_port_collector", "bgp_route_sync"], "prefers": ["dns_record_sync"],
                "category": "Network Infrastructure",
                "schedule": "Daily at 02:00 UTC",
                "task_group": "enrichment",
                "resources": device_fingerprint_enrichment_resources.resources,
            },
        )

        bandwidth_billing_aggregator = PythonOperator(
            task_id="bandwidth_billing_aggregator",
            python_callable=run_etl,
            params={
                "etl_name": "bandwidth_billing_aggregator",
                "category": "Bandwidth/Billing",
                "schedule": "Hourly",
                "needs": ["bgp_route_sync"],
                "prefers": ["dns_record_sync"],
            },
            op_kwargs={
                "etl_name": "bandwidth_billing_aggregator",
                "needs": ["bgp_route_sync"], "prefers": ["dns_record_sync"],
                "category": "Bandwidth/Billing",
                "schedule": "Hourly",
                "task_group": "enrichment",
                "resources": bandwidth_billing_aggregator_resources.resources,
            },
        )

        link_failure_prediction = PythonOperator(
            task_id="link_failure_prediction",
            python_callable=run_etl,
            params={
                "etl_name": "link_failure_prediction",
                "category": "Predictive Analytics",
                "schedule": "Daily at 05:00 UTC",
                "needs": ["device_fingerprint_enrichment"],
                "prefers": ["netflow_capture"],
            },
            op_kwargs={
                "etl_name": "link_failure_prediction",
                "needs": ["device_fingerprint_enrichment"], "prefers": ["netflow_capture"],
                "category": "Predictive Analytics",
                "schedule": "Daily at 05:00 UTC",
                "task_group": "enrichment",
                "resources": link_failure_prediction_resources.resources,
            },
        )

        bandwidth_cost_reconciliation = PythonOperator(
            task_id="bandwidth_cost_reconciliation",
            python_callable=run_etl,
            params={
                "etl_name": "bandwidth_cost_reconciliation",
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 04:00 UTC",
                "needs": ["bandwidth_billing_aggregator", "bgp_route_sync"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "bandwidth_cost_reconciliation",
                "needs": ["bandwidth_billing_aggregator", "bgp_route_sync"], "prefers": [],
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 04:00 UTC",
                "task_group": "enrichment",
                "resources": bandwidth_cost_reconciliation_resources.resources,
            },
        )

    # --- Delivery group (depth 4) — leaf nodes ---
    with TaskGroup("delivery", prefix_group_id=False) as delivery:
        noc_dashboard_snapshot = PythonOperator(
            task_id="noc_dashboard_snapshot",
            python_callable=run_etl,
            params={
                "etl_name": "noc_dashboard_snapshot",
                "category": "NOC Management",
                "schedule": "Daily at 06:00 UTC",
                "needs": ["bandwidth_cost_reconciliation", "link_failure_prediction"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "noc_dashboard_snapshot",
                "needs": ["bandwidth_cost_reconciliation", "link_failure_prediction"], "prefers": [],
                "category": "NOC Management",
                "schedule": "Daily at 06:00 UTC",
                "task_group": "delivery",
                "resources": noc_dashboard_snapshot_resources.resources,
            },
        )

        network_insights_api = PythonOperator(
            task_id="network_insights_api",
            python_callable=run_etl,
            params={
                "etl_name": "network_insights_api",
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "needs": ["device_fingerprint_enrichment", "link_failure_prediction"],
                "prefers": [],
            },
            op_kwargs={
                "etl_name": "network_insights_api",
                "needs": ["device_fingerprint_enrichment", "link_failure_prediction"], "prefers": [],
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "task_group": "delivery",
                "resources": network_insights_api_resources.resources,
            },
        )

        bandwidth_reports_api = PythonOperator(
            task_id="bandwidth_reports_api",
            python_callable=run_etl,
            params={
                "etl_name": "bandwidth_reports_api",
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "needs": ["bandwidth_cost_reconciliation"],
                "prefers": ["bandwidth_billing_aggregator"],
            },
            op_kwargs={
                "etl_name": "bandwidth_reports_api",
                "needs": ["bandwidth_cost_reconciliation"], "prefers": ["bandwidth_billing_aggregator"],
                "category": "Network APIs",
                "schedule": "On-demand (API)",
                "task_group": "delivery",
                "resources": bandwidth_reports_api_resources.resources,
            },
        )

    # --- Sensor wiring (sensors → root ETL tasks) ---
    switch_telemetry_sensor >> switch_port_collector
    bgp_feed_sensor >> bgp_route_sync
    netflow_collector_sensor >> netflow_capture
    dns_query_log_sensor >> dns_record_sync

    # --- Dependency wiring ---
    # Layer 0 → Layer 1
    switch_port_collector >> bgp_route_sync
    switch_port_collector >> dns_record_sync
    switch_port_collector >> netflow_capture

    # Layer 1 → Layer 2
    bgp_route_sync >> device_fingerprint_enrichment
    dns_record_sync >> device_fingerprint_enrichment
    bgp_route_sync >> bandwidth_billing_aggregator
    dns_record_sync >> bandwidth_billing_aggregator

    # Layer 2 → Layer 3
    device_fingerprint_enrichment >> link_failure_prediction
    netflow_capture >> link_failure_prediction
    bandwidth_billing_aggregator >> bandwidth_cost_reconciliation
    bgp_route_sync >> bandwidth_cost_reconciliation

    # Layer 3 → Layer 4
    link_failure_prediction >> noc_dashboard_snapshot
    bandwidth_cost_reconciliation >> noc_dashboard_snapshot
    device_fingerprint_enrichment >> network_insights_api
    link_failure_prediction >> network_insights_api
    bandwidth_cost_reconciliation >> bandwidth_reports_api
    bandwidth_billing_aggregator >> bandwidth_reports_api
