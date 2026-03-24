"""soc_monitoring — SOC real-time monitoring — syslog forensics and incident response analytics.

Monitors syslog event flow and DNS activity to keep network operations
teams informed. Runs hourly.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

from daily.task_configs import DnsIntelSync_task_config
from hourly.task_configs import SyslogCollector_task_config, IncidentForensicsRollup_task_config
from daily.resources import DnsIntelSync_resources
from hourly.resources import (
    SyslogCollector_resources,
    IncidentForensicsRollup_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=2),
}


with DAG(
    dag_id="soc_monitoring",
    default_args=default_args,
    description="SOC real-time monitoring — syslog forensics and incident response analytics",
    schedule="0 * * * *",
    start_date=datetime(2026, 3, 8),
    catchup=False,
) as dag:

    # --- Bouncers group (data ingestion) ---
    with TaskGroup("Oasis-Bouncers", prefix_group_id=True) as bouncers:
        SyslogReceiverBouncer = PythonOperator(
            task_id="SyslogReceiverBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SyslogReceiverBouncer",
                "description": "Receives syslog messages from network devices and firewalls",
            },
        )

        DnsQueryLogBouncer = PythonOperator(
            task_id="DnsQueryLogBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "DnsQueryLogBouncer",
                "description": "Taps DNS resolver query logs for resolution analytics",
            },
        )

    # --- Monitoring group (ETL tasks) ---
    with TaskGroup("Oasis-Monitoring", prefix_group_id=True) as monitoring:
        SyslogCollector = PythonOperator(
            task_id="SyslogCollector",
            python_callable=run_etl,
            params={
                "needs": SyslogCollector_task_config.needs,
                "prefers": SyslogCollector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SyslogCollector",
                "resources": SyslogCollector_resources.resources,
            },
        )

        DnsIntelSync = PythonOperator(
            task_id="DnsIntelSync",
            python_callable=run_etl,
            params={
                "needs": DnsIntelSync_task_config.needs,
                "prefers": DnsIntelSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsIntelSync",
                "resources": DnsIntelSync_resources.resources,
            },
        )

        IncidentForensicsRollup = PythonOperator(
            task_id="IncidentForensicsRollup",
            python_callable=run_etl,
            params={
                "needs": IncidentForensicsRollup_task_config.needs,
                "prefers": IncidentForensicsRollup_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "IncidentForensicsRollup",
                "resources": IncidentForensicsRollup_resources.resources,
            },
        )

    # Bouncer wiring
    SyslogReceiverBouncer >> SyslogCollector
    DnsQueryLogBouncer >> DnsIntelSync

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "SyslogCollector": SyslogCollector,
        "DnsIntelSync": DnsIntelSync,
        "IncidentForensicsRollup": IncidentForensicsRollup,
    }
    task_cfgs = {
        "SyslogCollector": SyslogCollector_task_config,
        "DnsIntelSync": DnsIntelSync_task_config,
        "IncidentForensicsRollup": IncidentForensicsRollup_task_config,
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
