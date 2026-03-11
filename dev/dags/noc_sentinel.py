"""noc_sentinel — Network Operations Center real-time monitoring pipeline.

Monitors syslog event flow and DNS activity to keep network operations
teams informed. Runs hourly.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_sensor

from daily.task_configs import DnsRecordSync_task_config
from hourly.task_configs import SyslogEventStream_task_config, IncidentAnalyticsRollup_task_config
from daily.resources import DnsRecordSync_resources
from hourly.resources import (
    SyslogEventStream_resources,
    IncidentAnalyticsRollup_resources,
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

    # --- Sensors group (data ingestion) ---
    with TaskGroup("OasisSensors", prefix_group_id=False) as sensors:
        SyslogReceiverSensor = PythonOperator(
            task_id="SyslogReceiverSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "SyslogReceiverSensor",
                "team": "Vault",
                "description": "Receives syslog messages from network devices and firewalls",
            },
            op_kwargs={
                "sensor_name": "SyslogReceiverSensor",
                "team": "Vault",
                "description": "Receives syslog messages from network devices and firewalls",
                "volume_per_day": 8_500_000,
            },
        )

        DnsQueryLogSensor = PythonOperator(
            task_id="DnsQueryLogSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "DnsQueryLogSensor",
                "team": "Prism",
                "description": "Taps DNS resolver query logs for resolution analytics",
            },
            op_kwargs={
                "sensor_name": "DnsQueryLogSensor",
                "team": "Prism",
                "description": "Taps DNS resolver query logs for resolution analytics",
                "volume_per_day": 12_000_000,
            },
        )

    # --- Monitoring group (ETL tasks) ---
    with TaskGroup("OasisMonitoring", prefix_group_id=False) as monitoring:
        SyslogEventStream = PythonOperator(
            task_id="SyslogEventStream",
            python_callable=run_etl,
            params={
                "etl_name": "SyslogEventStream",
                "category": "Incident Management",
                "schedule": "Real-time (Streaming)",
                "needs": SyslogEventStream_task_config.needs,
                "prefers": SyslogEventStream_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SyslogEventStream",
                "needs": SyslogEventStream_task_config.needs, "prefers": SyslogEventStream_task_config.prefers,
                "category": "Incident Management",
                "schedule": "Real-time (Streaming)",
                "resources": SyslogEventStream_resources.resources,
            },
        )

        DnsRecordSync = PythonOperator(
            task_id="DnsRecordSync",
            python_callable=run_etl,
            params={
                "etl_name": "DnsRecordSync",
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "needs": DnsRecordSync_task_config.needs,
                "prefers": DnsRecordSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsRecordSync",
                "needs": DnsRecordSync_task_config.needs, "prefers": DnsRecordSync_task_config.prefers,
                "category": "DNS/Resolution",
                "schedule": "Hourly",
                "resources": DnsRecordSync_resources.resources,
            },
        )

        IncidentAnalyticsRollup = PythonOperator(
            task_id="IncidentAnalyticsRollup",
            python_callable=run_etl,
            params={
                "etl_name": "IncidentAnalyticsRollup",
                "category": "Incident Management",
                "schedule": "Hourly",
                "needs": IncidentAnalyticsRollup_task_config.needs,
                "prefers": IncidentAnalyticsRollup_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "IncidentAnalyticsRollup",
                "needs": IncidentAnalyticsRollup_task_config.needs, "prefers": IncidentAnalyticsRollup_task_config.prefers,
                "category": "Incident Management",
                "schedule": "Hourly",
                "resources": IncidentAnalyticsRollup_resources.resources,
            },
        )

    # Sensor wiring
    SyslogReceiverSensor >> SyslogEventStream
    DnsQueryLogSensor >> DnsRecordSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SyslogEventStream": SyslogEventStream,
        "DnsRecordSync": DnsRecordSync,
        "IncidentAnalyticsRollup": IncidentAnalyticsRollup,
    }
    task_cfgs = {
        "SyslogEventStream": SyslogEventStream_task_config,
        "DnsRecordSync": DnsRecordSync_task_config,
        "IncidentAnalyticsRollup": IncidentAnalyticsRollup_task_config,
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
