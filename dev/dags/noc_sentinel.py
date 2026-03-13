"""noc_sentinel — Network Operations Center real-time monitoring pipeline.

Monitors syslog event flow and DNS activity to keep network operations
teams informed. Runs hourly.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl
from sensor_runner import run_bouncer

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
        SyslogEventStream = PythonOperator(
            task_id="SyslogEventStream",
            python_callable=run_etl,
            params={
                "needs": SyslogEventStream_task_config.needs,
                "prefers": SyslogEventStream_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SyslogEventStream",
                "resources": SyslogEventStream_resources.resources,
            },
        )

        DnsRecordSync = PythonOperator(
            task_id="DnsRecordSync",
            python_callable=run_etl,
            params={
                "needs": DnsRecordSync_task_config.needs,
                "prefers": DnsRecordSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DnsRecordSync",
                "resources": DnsRecordSync_resources.resources,
            },
        )

        IncidentAnalyticsRollup = PythonOperator(
            task_id="IncidentAnalyticsRollup",
            python_callable=run_etl,
            params={
                "needs": IncidentAnalyticsRollup_task_config.needs,
                "prefers": IncidentAnalyticsRollup_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "IncidentAnalyticsRollup",
                "resources": IncidentAnalyticsRollup_resources.resources,
            },
        )

    # Bouncer wiring
    SyslogReceiverBouncer >> SyslogEventStream
    DnsQueryLogBouncer >> DnsRecordSync

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
