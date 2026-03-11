"""heartbeat_probe — Network heartbeat & keepalive probe pipeline.

Captures infrastructure telemetry and flow data to power
network monitoring dashboards. Runs every 4 hours.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_sensor

from daily.task_configs import SwitchPortCollector_task_config
from hourly.task_configs import NetflowCapture_task_config
from daily.resources import SwitchPortCollector_resources
from hourly.resources import NetflowCapture_resources

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

        SnmpTrapSensor = PythonOperator(
            task_id="SnmpTrapSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "SnmpTrapSensor",
                "team": "Oasis",
                "description": "Receives SNMP trap notifications for device health events",
            },
            op_kwargs={
                "sensor_name": "SnmpTrapSensor",
                "team": "Oasis",
                "description": "Receives SNMP trap notifications for device health events",
                "volume_per_day": 420_000,
            },
        )

    # --- Probes group (ETL tasks) ---
    with TaskGroup("DaggerProbes", prefix_group_id=False) as probes:
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

    # Sensor wiring
    SwitchTelemetrySensor >> SwitchPortCollector
    SnmpTrapSensor >> SwitchPortCollector

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SwitchPortCollector": SwitchPortCollector,
        "NetflowCapture": NetflowCapture,
    }
    task_cfgs = {
        "SwitchPortCollector": SwitchPortCollector_task_config,
        "NetflowCapture": NetflowCapture_task_config,
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
