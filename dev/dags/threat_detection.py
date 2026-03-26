"""threat_detection — Threat detection pipeline — threat hunting, access log forensics, intrusion attribution.

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
from sensor_runner import run_bouncer

from daily.task_configs import (
    DhcpLeaseRecon_task_config,
    AccessLogCollector_task_config,
    TrafficAttributionAnalyzer_task_config,
    ThreatHunterScorer_task_config,
    PeeringIntelCalculator_task_config,
    CapacityThreatForecast_task_config,
    MacIntelEnrichment_task_config,
    WeeklyThreatDigest_task_config,
    CdnAuditReconciler_task_config,
)
from daily.resources import (
    DhcpLeaseRecon_resources,
    AccessLogCollector_resources,
    TrafficAttributionAnalyzer_resources,
    ThreatHunterScorer_resources,
    PeeringIntelCalculator_resources,
    CapacityThreatForecast_resources,
    MacIntelEnrichment_resources,
    WeeklyThreatDigest_resources,
    CdnAuditReconciler_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="threat_detection",
    default_args=default_args,
    description="Threat detection pipeline — threat hunting, access log forensics, intrusion attribution",
    schedule="0 2 * * *",
    start_date=datetime(2026, 3, 24),
    catchup=True,
) as dag:

    # --- Bouncers group (data ingestion) ---
    with TaskGroup("Vault-Bouncers", prefix_group_id=True) as bouncers:
        SyslogReceiverBouncer = PythonOperator(
            task_id="SyslogReceiverBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "SyslogReceiverBouncer",
                "description": "Receives syslog messages from network devices and firewalls",
            },
        )

        FirewallEventBouncer = PythonOperator(
            task_id="FirewallEventBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "FirewallEventBouncer",
                "description": "Captures firewall rule hit events and connection logs",
            },
        )

        HttpAccessLogBouncer = PythonOperator(
            task_id="HttpAccessLogBouncer",
            python_callable=run_bouncer,
            op_kwargs={
                "sensor_name": "HttpAccessLogBouncer",
                "description": "Ingests HTTP proxy and CDN access logs",
            },
        )

    # --- Sources group (depth 0) — two independent sources ---
    with TaskGroup("Vault-Sources", prefix_group_id=True) as sources:
        # SCENARIO 1: Flaky source — fails with RuntimeError (simulates DHCP server timeout)
        DhcpLeaseRecon = PythonOperator(
            task_id="DhcpLeaseRecon",
            python_callable=run_etl,
            params={
                "needs": DhcpLeaseRecon_task_config.needs,
                "prefers": DhcpLeaseRecon_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DhcpLeaseRecon",
                "resources": DhcpLeaseRecon_resources.resources,
                "simulate_failure": "DHCP server timeout after 30s — lease pool exhausted (429 Too Many Requests)",
            },
        )

        # SCENARIO 2: Reliable source — always succeeds
        AccessLogCollector = PythonOperator(
            task_id="AccessLogCollector",
            python_callable=run_etl,
            params={
                "needs": AccessLogCollector_task_config.needs,
                "prefers": AccessLogCollector_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "AccessLogCollector",
                "resources": AccessLogCollector_resources.resources,
            },
        )

    # --- Analysis group (depth 1) ---
    with TaskGroup("Vault-Analysis", prefix_group_id=True) as analysis:
        # SCENARIO 3: Prefers failed, needs succeeded → still works
        TrafficAttributionAnalyzer = PythonOperator(
            task_id="TrafficAttributionAnalyzer",
            python_callable=run_etl,
            params={
                "needs": TrafficAttributionAnalyzer_task_config.needs,
                "prefers": TrafficAttributionAnalyzer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "TrafficAttributionAnalyzer",
                "resources": TrafficAttributionAnalyzer_resources.resources,
            },
        )

        # SCENARIO 4: Need failed → cascading upstream_failed
        ThreatHunterScorer = PythonOperator(
            task_id="ThreatHunterScorer",
            python_callable=run_etl,
            params={
                "needs": ThreatHunterScorer_task_config.needs,
                "prefers": ThreatHunterScorer_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ThreatHunterScorer",
                "resources": ThreatHunterScorer_resources.resources,
            },
        )

        # SCENARIO 7: Both needs failed (dhcp + http needed) → upstream_failed
        MacIntelEnrichment = PythonOperator(
            task_id="MacIntelEnrichment",
            python_callable=run_etl,
            params={
                "needs": MacIntelEnrichment_task_config.needs,
                "prefers": MacIntelEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "MacIntelEnrichment",
                "resources": MacIntelEnrichment_resources.resources,
            },
        )

        # SCENARIO 9: Intermittent — succeeds some runs, fails others (~40% failure rate)
        CdnAuditReconciler = PythonOperator(
            task_id="CdnAuditReconciler",
            python_callable=run_etl,
            params={
                "needs": CdnAuditReconciler_task_config.needs,
                "prefers": CdnAuditReconciler_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CdnAuditReconciler",
                "resources": CdnAuditReconciler_resources.resources,
                "simulate_flaky": "CDN provider billing API — intermittent 503 Service Unavailable",
            },
        )

    # --- Output group (depth 2-3) ---
    with TaskGroup("Vault-Output", prefix_group_id=True) as output:
        # SCENARIO 5: All needs succeeded → normal happy path
        PeeringIntelCalculator = PythonOperator(
            task_id="PeeringIntelCalculator",
            python_callable=run_etl,
            params={
                "needs": PeeringIntelCalculator_task_config.needs,
                "prefers": PeeringIntelCalculator_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "PeeringIntelCalculator",
                "resources": PeeringIntelCalculator_resources.resources,
            },
        )

        # SCENARIO 6: One of two needs failed → upstream_failed
        CapacityThreatForecast = PythonOperator(
            task_id="CapacityThreatForecast",
            python_callable=run_etl,
            params={
                "needs": CapacityThreatForecast_task_config.needs,
                "prefers": CapacityThreatForecast_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CapacityThreatForecast",
                "resources": CapacityThreatForecast_resources.resources,
            },
        )

        # SCENARIO 8: Needs ok, multiple prefers failed → still works
        WeeklyThreatDigest = PythonOperator(
            task_id="WeeklyThreatDigest",
            python_callable=run_etl,
            params={
                "needs": WeeklyThreatDigest_task_config.needs,
                "prefers": WeeklyThreatDigest_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "WeeklyThreatDigest",
                "resources": WeeklyThreatDigest_resources.resources,
            },
        )

    # --- Bouncer wiring (bouncers → root ETL tasks) ---
    FirewallEventBouncer >> DhcpLeaseRecon
    SyslogReceiverBouncer >> DhcpLeaseRecon
    HttpAccessLogBouncer >> AccessLogCollector

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "DhcpLeaseRecon": DhcpLeaseRecon,
        "AccessLogCollector": AccessLogCollector,
        "TrafficAttributionAnalyzer": TrafficAttributionAnalyzer,
        "ThreatHunterScorer": ThreatHunterScorer,
        "MacIntelEnrichment": MacIntelEnrichment,
        "CdnAuditReconciler": CdnAuditReconciler,
        "PeeringIntelCalculator": PeeringIntelCalculator,
        "CapacityThreatForecast": CapacityThreatForecast,
        "WeeklyThreatDigest": WeeklyThreatDigest,
    }
    task_cfgs = {
        "DhcpLeaseRecon": DhcpLeaseRecon_task_config,
        "AccessLogCollector": AccessLogCollector_task_config,
        "TrafficAttributionAnalyzer": TrafficAttributionAnalyzer_task_config,
        "ThreatHunterScorer": ThreatHunterScorer_task_config,
        "MacIntelEnrichment": MacIntelEnrichment_task_config,
        "CdnAuditReconciler": CdnAuditReconciler_task_config,
        "PeeringIntelCalculator": PeeringIntelCalculator_task_config,
        "CapacityThreatForecast": CapacityThreatForecast_task_config,
        "WeeklyThreatDigest": WeeklyThreatDigest_task_config,
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
