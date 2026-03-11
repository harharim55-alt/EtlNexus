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
    DhcpLeaseSync_task_config,
    HttpAccessLogIngest_task_config,
    TrafficAttributionModel_task_config,
    ThreatScoringPipeline_task_config,
    PeeringRoiCalculator_task_config,
    CapacityPlanningForecast_task_config,
    MacAddressEnrichment_task_config,
    WeeklyNetworkDigest_task_config,
    CdnCostReconciler_task_config,
)
from daily.resources import (
    DhcpLeaseSync_resources,
    HttpAccessLogIngest_resources,
    TrafficAttributionModel_resources,
    ThreatScoringPipeline_resources,
    PeeringRoiCalculator_resources,
    CapacityPlanningForecast_resources,
    MacAddressEnrichment_resources,
    WeeklyNetworkDigest_resources,
    CdnCostReconciler_resources,
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
    with TaskGroup("VaultSensors", prefix_group_id=False) as sensors:
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

        FirewallEventSensor = PythonOperator(
            task_id="FirewallEventSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "FirewallEventSensor",
                "team": "Vault",
                "description": "Captures firewall rule hit events and connection logs",
            },
            op_kwargs={
                "sensor_name": "FirewallEventSensor",
                "team": "Vault",
                "description": "Captures firewall rule hit events and connection logs",
                "volume_per_day": 3_100_000,
            },
        )

        HttpAccessLogSensor = PythonOperator(
            task_id="HttpAccessLogSensor",
            python_callable=run_sensor,
            params={
                "sensor_name": "HttpAccessLogSensor",
                "team": "Oasis",
                "description": "Ingests HTTP proxy and CDN access logs",
            },
            op_kwargs={
                "sensor_name": "HttpAccessLogSensor",
                "team": "Oasis",
                "description": "Ingests HTTP proxy and CDN access logs",
                "volume_per_day": 18_000_000,
            },
        )

    # --- Sources group (depth 0) — two independent sources ---
    with TaskGroup("VaultSources", prefix_group_id=False) as sources:
        # SCENARIO 1: Flaky source — fails with RuntimeError (simulates DHCP server timeout)
        DhcpLeaseSync = PythonOperator(
            task_id="DhcpLeaseSync",
            python_callable=run_etl,
            params={
                "etl_name": "DhcpLeaseSync",
                "category": "Address Management",
                "schedule": "Daily at 02:00 UTC",
                "needs": DhcpLeaseSync_task_config.needs,
                "prefers": DhcpLeaseSync_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DhcpLeaseSync",
                "needs": DhcpLeaseSync_task_config.needs, "prefers": DhcpLeaseSync_task_config.prefers,
                "category": "Address Management",
                "schedule": "Daily at 02:00 UTC",
                "resources": DhcpLeaseSync_resources.resources,
                "simulate_failure": "DHCP server timeout after 30s — lease pool exhausted (429 Too Many Requests)",
            },
        )

        # SCENARIO 2: Reliable source — always succeeds
        HttpAccessLogIngest = PythonOperator(
            task_id="HttpAccessLogIngest",
            python_callable=run_etl,
            params={
                "etl_name": "HttpAccessLogIngest",
                "category": "Traffic Analytics",
                "schedule": "Daily at 02:00 UTC",
                "needs": HttpAccessLogIngest_task_config.needs,
                "prefers": HttpAccessLogIngest_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "HttpAccessLogIngest",
                "needs": HttpAccessLogIngest_task_config.needs, "prefers": HttpAccessLogIngest_task_config.prefers,
                "category": "Traffic Analytics",
                "schedule": "Daily at 02:00 UTC",
                "resources": HttpAccessLogIngest_resources.resources,
            },
        )

    # --- Analysis group (depth 1) ---
    with TaskGroup("VaultAnalysis", prefix_group_id=False) as analysis:
        # SCENARIO 3: Prefers failed, needs succeeded → still works
        # Uses trigger_rule="all_done" to tolerate DhcpLeaseSync failure
        TrafficAttributionModel = PythonOperator(
            task_id="TrafficAttributionModel",
            python_callable=run_etl,
            params={
                "etl_name": "TrafficAttributionModel",
                "category": "Traffic Engineering",
                "schedule": "Daily at 02:30 UTC",
                "needs": TrafficAttributionModel_task_config.needs,
                "prefers": TrafficAttributionModel_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "TrafficAttributionModel",
                "needs": TrafficAttributionModel_task_config.needs, "prefers": TrafficAttributionModel_task_config.prefers,
                "category": "Traffic Engineering",
                "schedule": "Daily at 02:30 UTC",
                "resources": TrafficAttributionModel_resources.resources,
            },
        )

        # SCENARIO 4: Need failed → cascading upstream_failed
        ThreatScoringPipeline = PythonOperator(
            task_id="ThreatScoringPipeline",
            python_callable=run_etl,
            params={
                "etl_name": "ThreatScoringPipeline",
                "category": "Predictive Analytics",
                "schedule": "Daily at 02:30 UTC",
                "needs": ThreatScoringPipeline_task_config.needs,
                "prefers": ThreatScoringPipeline_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ThreatScoringPipeline",
                "needs": ThreatScoringPipeline_task_config.needs, "prefers": ThreatScoringPipeline_task_config.prefers,
                "category": "Predictive Analytics",
                "schedule": "Daily at 02:30 UTC",
                "resources": ThreatScoringPipeline_resources.resources,
            },
        )

        # SCENARIO 7: Both needs failed (dhcp + http needed) → upstream_failed
        MacAddressEnrichment = PythonOperator(
            task_id="MacAddressEnrichment",
            python_callable=run_etl,
            params={
                "etl_name": "MacAddressEnrichment",
                "category": "Address Management",
                "schedule": "Daily at 02:30 UTC",
                "needs": MacAddressEnrichment_task_config.needs,
                "prefers": MacAddressEnrichment_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "MacAddressEnrichment",
                "needs": MacAddressEnrichment_task_config.needs, "prefers": MacAddressEnrichment_task_config.prefers,
                "category": "Address Management",
                "schedule": "Daily at 02:30 UTC",
                "resources": MacAddressEnrichment_resources.resources,
            },
        )

        # SCENARIO 9: Intermittent — succeeds some runs, fails others (~40% failure rate)
        # Simulates a flaky CDN provider billing API
        CdnCostReconciler = PythonOperator(
            task_id="CdnCostReconciler",
            python_callable=run_etl,
            params={
                "etl_name": "CdnCostReconciler",
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 02:30 UTC",
                "needs": CdnCostReconciler_task_config.needs,
                "prefers": CdnCostReconciler_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CdnCostReconciler",
                "needs": CdnCostReconciler_task_config.needs, "prefers": CdnCostReconciler_task_config.prefers,
                "category": "Bandwidth/Billing",
                "schedule": "Daily at 02:30 UTC",
                "resources": CdnCostReconciler_resources.resources,
                "simulate_flaky": "CDN provider billing API — intermittent 503 Service Unavailable",
            },
        )

    # --- Output group (depth 2-3) ---
    with TaskGroup("VaultOutput", prefix_group_id=False) as output:
        # SCENARIO 5: All needs succeeded → normal happy path
        PeeringRoiCalculator = PythonOperator(
            task_id="PeeringRoiCalculator",
            python_callable=run_etl,
            params={
                "etl_name": "PeeringRoiCalculator",
                "category": "Traffic Engineering",
                "schedule": "Daily at 03:00 UTC",
                "needs": PeeringRoiCalculator_task_config.needs,
                "prefers": PeeringRoiCalculator_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "PeeringRoiCalculator",
                "needs": PeeringRoiCalculator_task_config.needs, "prefers": PeeringRoiCalculator_task_config.prefers,
                "category": "Traffic Engineering",
                "schedule": "Daily at 03:00 UTC",
                "resources": PeeringRoiCalculator_resources.resources,
            },
        )

        # SCENARIO 6: One of two needs failed → upstream_failed
        CapacityPlanningForecast = PythonOperator(
            task_id="CapacityPlanningForecast",
            python_callable=run_etl,
            params={
                "etl_name": "CapacityPlanningForecast",
                "category": "Predictive Analytics",
                "schedule": "Daily at 03:00 UTC",
                "needs": CapacityPlanningForecast_task_config.needs,
                "prefers": CapacityPlanningForecast_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CapacityPlanningForecast",
                "needs": CapacityPlanningForecast_task_config.needs, "prefers": CapacityPlanningForecast_task_config.prefers,
                "category": "Predictive Analytics",
                "schedule": "Daily at 03:00 UTC",
                "resources": CapacityPlanningForecast_resources.resources,
            },
        )

        # SCENARIO 8: Needs ok, multiple prefers failed → still works
        # Uses trigger_rule="all_done" to tolerate capacity_planning and mac_address failures
        WeeklyNetworkDigest = PythonOperator(
            task_id="WeeklyNetworkDigest",
            python_callable=run_etl,
            params={
                "etl_name": "WeeklyNetworkDigest",
                "category": "NOC Management",
                "schedule": "Daily at 03:30 UTC",
                "needs": WeeklyNetworkDigest_task_config.needs,
                "prefers": WeeklyNetworkDigest_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "WeeklyNetworkDigest",
                "needs": WeeklyNetworkDigest_task_config.needs, "prefers": WeeklyNetworkDigest_task_config.prefers,
                "category": "NOC Management",
                "schedule": "Daily at 03:30 UTC",
                "resources": WeeklyNetworkDigest_resources.resources,
            },
        )

    # --- Sensor wiring (sensors → root ETL tasks) ---
    FirewallEventSensor >> DhcpLeaseSync
    SyslogReceiverSensor >> DhcpLeaseSync
    HttpAccessLogSensor >> HttpAccessLogIngest

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "DhcpLeaseSync": DhcpLeaseSync,
        "HttpAccessLogIngest": HttpAccessLogIngest,
        "TrafficAttributionModel": TrafficAttributionModel,
        "ThreatScoringPipeline": ThreatScoringPipeline,
        "MacAddressEnrichment": MacAddressEnrichment,
        "CdnCostReconciler": CdnCostReconciler,
        "PeeringRoiCalculator": PeeringRoiCalculator,
        "CapacityPlanningForecast": CapacityPlanningForecast,
        "WeeklyNetworkDigest": WeeklyNetworkDigest,
    }
    task_cfgs = {
        "DhcpLeaseSync": DhcpLeaseSync_task_config,
        "HttpAccessLogIngest": HttpAccessLogIngest_task_config,
        "TrafficAttributionModel": TrafficAttributionModel_task_config,
        "ThreatScoringPipeline": ThreatScoringPipeline_task_config,
        "MacAddressEnrichment": MacAddressEnrichment_task_config,
        "CdnCostReconciler": CdnCostReconciler_task_config,
        "PeeringRoiCalculator": PeeringRoiCalculator_task_config,
        "CapacityPlanningForecast": CapacityPlanningForecast_task_config,
        "WeeklyNetworkDigest": WeeklyNetworkDigest_task_config,
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
