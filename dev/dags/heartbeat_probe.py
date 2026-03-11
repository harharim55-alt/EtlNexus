"""heartbeat_probe — Network heartbeat & keepalive probe pipeline.

Captures infrastructure telemetry and flow data to power
network monitoring dashboards. Runs every 4 hours.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

from etl_runner import run_etl
from sensor_runner import run_sensor

from hourly.task_configs import netflow_capture_task_config
from daily.resources import switch_port_collector_resources
from hourly.resources import netflow_capture_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="heartbeat_probe",
    default_args=default_args,
    description="Network heartbeat & keepalive probes",
    schedule="0 */4 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
) as dag:

    # --- Sensors (data ingestion) ---
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

    snmp_trap_sensor = PythonOperator(
        task_id="snmp_trap_sensor",
        python_callable=run_sensor,
        params={
            "sensor_name": "snmp_trap_sensor",
            "team": "NOC Operations",
            "description": "Receives SNMP trap notifications for device health events",
        },
        op_kwargs={
            "sensor_name": "snmp_trap_sensor",
            "team": "NOC Operations",
            "description": "Receives SNMP trap notifications for device health events",
            "volume_per_day": 420_000,
        },
    )

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

    # Sensor wiring
    switch_telemetry_sensor >> switch_port_collector
    snmp_trap_sensor >> switch_port_collector

    # Dependencies derived from task configs:
    # netflow_capture needs switch_port_collector
    switch_port_collector >> netflow_capture
