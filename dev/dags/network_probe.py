"""network_probe — Infrastructure telemetry sweeps and flow interception.

Captures infrastructure telemetry and flow data to power
network monitoring dashboards. Runs every 4 hours.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

from daily.task_configs import PortScanCollector_task_config
from hourly.task_configs import FlowInterceptor_task_config
from daily.resources import PortScanCollector_resources
from hourly.resources import FlowInterceptor_resources

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="network_probe",
    default_args=default_args,
    description="Infrastructure telemetry sweeps and flow interception",
    schedule="0 */4 * * *",
    start_date=datetime(2026, 3, 8),
    catchup=True,
) as dag:

    # --- Bouncers group (data ingestion) ---
    with TaskGroup("Dagger-Bouncers", prefix_group_id=True) as bouncers:
        SwitchTelemetryBouncer = PythonOperator(
            task_id="SwitchTelemetryBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SwitchTelemetryBouncer",
                "description": "Streams switch interface telemetry via gNMI/SNMP polling",
            },
        )

        SnmpTrapBouncer = PythonOperator(
            task_id="SnmpTrapBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SnmpTrapBouncer",
                "description": "Receives SNMP trap notifications for device health events",
            },
        )

    # --- Probes group (ETL tasks) ---
    with TaskGroup("Dagger-Probes", prefix_group_id=True) as probes:
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

    # Bouncer wiring
    SwitchTelemetryBouncer >> PortScanCollector
    SnmpTrapBouncer >> PortScanCollector

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "PortScanCollector": PortScanCollector,
        "FlowInterceptor": FlowInterceptor,
    }
    task_cfgs = {
        "PortScanCollector": PortScanCollector_task_config,
        "FlowInterceptor": FlowInterceptor_task_config,
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
