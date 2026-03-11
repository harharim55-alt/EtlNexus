"""noc_sentinel — Network Operations Center real-time monitoring pipeline.

Monitors syslog event flow and DNS activity to keep network operations
teams informed. Runs hourly.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_runner import run_etl
from sensor_runner import run_sensor

from hourly.task_configs import syslog_event_stream_task_config, incident_analytics_rollup_task_config
from daily.resources import dns_record_sync_resources
from hourly.resources import (
    syslog_event_stream_resources,
    incident_analytics_rollup_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="noc_sentinel",
    default_args=default_args,
    description="NOC real-time monitoring & incident analytics",
    schedule="0 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    # --- Sensors (data ingestion) ---
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

    syslog_event_stream = PythonOperator(
        task_id="syslog_event_stream",
        python_callable=run_etl,
        params={
            "etl_name": "syslog_event_stream",
            "category": "Incident Management",
            "schedule": "Real-time (Streaming)",
            "needs": [],
            "prefers": ["dns_record_sync"],
        },
        op_kwargs={
            "etl_name": "syslog_event_stream",
            "needs": [], "prefers": ["dns_record_sync"],
            "category": "Incident Management",
            "schedule": "Real-time (Streaming)",
            "resources": syslog_event_stream_resources.resources,
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
            "resources": dns_record_sync_resources.resources,
        },
    )

    incident_analytics_rollup = PythonOperator(
        task_id="incident_analytics_rollup",
        python_callable=run_etl,
        params={
            "etl_name": "incident_analytics_rollup",
            "category": "Incident Management",
            "schedule": "Hourly",
            "needs": ["syslog_event_stream"],
            "prefers": ["dns_record_sync"],
        },
        op_kwargs={
            "etl_name": "incident_analytics_rollup",
            "needs": ["syslog_event_stream"], "prefers": ["dns_record_sync"],
            "category": "Incident Management",
            "schedule": "Hourly",
            "resources": incident_analytics_rollup_resources.resources,
        },
    )

    # Sensor wiring
    syslog_receiver_sensor >> syslog_event_stream
    dns_query_log_sensor >> dns_record_sync

    # Dependencies derived from task configs:
    # syslog_event_stream prefers dns_record_sync (soft dep)
    # incident_analytics_rollup needs syslog_event_stream, prefers dns_record_sync
    syslog_event_stream >> incident_analytics_rollup
    dns_record_sync >> incident_analytics_rollup
