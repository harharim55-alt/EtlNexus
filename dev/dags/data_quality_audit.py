"""data_quality_audit — Data quality and compliance auditing pipeline.

Comprehensive data quality pipeline that validates schema compliance, profiles
field distributions, audits cross-team join integrity, detects anomalies via
Pandas UDFs, and produces a unified quality scorecard. Exercises every PySpark
execution plan node type: Sample, Except, Intersect, Deduplicate, Cache/Persist,
Range, LocalTableScan, BroadcastHashJoin, SortMergeJoin, CartesianProduct,
Pivot, Unpivot, Rollup, Cube, explode, posexplode, pandas_udf, applyInPandas,
Window, Repartition, Coalesce, Union, Filter, Project, Sort, Limit.

Runs daily at 03:00 UTC with dependency depth 4.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup

from etl_runner import run_etl

from daily.task_configs import (
    AssetInventorySnapshot_task_config,
    SchemaComplianceChecker_task_config,
    FieldFrequencyProfiler_task_config,
    CrossTeamJoinAuditor_task_config,
    ComplianceMetricsPivot_task_config,
    AnomalyPatternMiner_task_config,
    DataQualityScorecard_task_config,
    QualityAlertApiDummy_task_config,
)
from daily.resources import (
    AssetInventorySnapshot_resources,
    SchemaComplianceChecker_resources,
    FieldFrequencyProfiler_resources,
    CrossTeamJoinAuditor_resources,
    ComplianceMetricsPivot_resources,
    AnomalyPatternMiner_resources,
    DataQualityScorecard_resources,
    QualityAlertApiDummy_resources,
)

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "retries": 0,
    "retry_delay": timedelta(minutes=5),
}


with DAG(
    dag_id="data_quality_audit",
    default_args=default_args,
    description="Data quality and compliance auditing — schema validation, field profiling, cross-team join audits, anomaly detection",
    schedule="0 3 * * *",
    start_date=datetime(2026, 3, 24),
    catchup=True,
    tags=["category:Quality"],
) as dag:

    # --- Sources group (depth 0) ---
    with TaskGroup("Relay-Sources", prefix_group_id=True) as sources:
        AssetInventorySnapshot = PythonOperator(
            task_id="AssetInventorySnapshot",
            python_callable=run_etl,
            params={
                "needs": AssetInventorySnapshot_task_config.needs,
                "prefers": AssetInventorySnapshot_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "AssetInventorySnapshot",
                "resources": AssetInventorySnapshot_resources.resources,
            },
        )

    # --- Profiling group (depth 1) ---
    with TaskGroup("Relay-Profiling", prefix_group_id=True) as profiling:
        SchemaComplianceChecker = PythonOperator(
            task_id="SchemaComplianceChecker",
            python_callable=run_etl,
            params={
                "needs": SchemaComplianceChecker_task_config.needs,
                "prefers": SchemaComplianceChecker_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "SchemaComplianceChecker",
                "resources": SchemaComplianceChecker_resources.resources,
            },
        )

        FieldFrequencyProfiler = PythonOperator(
            task_id="FieldFrequencyProfiler",
            python_callable=run_etl,
            params={
                "needs": FieldFrequencyProfiler_task_config.needs,
                "prefers": FieldFrequencyProfiler_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "FieldFrequencyProfiler",
                "resources": FieldFrequencyProfiler_resources.resources,
            },
        )

    # --- Auditing group (depth 2) ---
    with TaskGroup("Relay-Auditing", prefix_group_id=True) as auditing:
        CrossTeamJoinAuditor = PythonOperator(
            task_id="CrossTeamJoinAuditor",
            python_callable=run_etl,
            params={
                "needs": CrossTeamJoinAuditor_task_config.needs,
                "prefers": CrossTeamJoinAuditor_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "CrossTeamJoinAuditor",
                "resources": CrossTeamJoinAuditor_resources.resources,
            },
        )

        AnomalyPatternMiner = PythonOperator(
            task_id="AnomalyPatternMiner",
            python_callable=run_etl,
            params={
                "needs": AnomalyPatternMiner_task_config.needs,
                "prefers": AnomalyPatternMiner_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "AnomalyPatternMiner",
                "resources": AnomalyPatternMiner_resources.resources,
            },
        )

    # --- Reporting group (depth 3) ---
    with TaskGroup("Relay-Reporting", prefix_group_id=True) as reporting:
        ComplianceMetricsPivot = PythonOperator(
            task_id="ComplianceMetricsPivot",
            python_callable=run_etl,
            params={
                "needs": ComplianceMetricsPivot_task_config.needs,
                "prefers": ComplianceMetricsPivot_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "ComplianceMetricsPivot",
                "resources": ComplianceMetricsPivot_resources.resources,
            },
        )

        DataQualityScorecard = PythonOperator(
            task_id="DataQualityScorecard",
            python_callable=run_etl,
            params={
                "needs": DataQualityScorecard_task_config.needs,
                "prefers": DataQualityScorecard_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "DataQualityScorecard",
                "resources": DataQualityScorecard_resources.resources,
            },
        )

    # --- API group (depth 4) ---
    with TaskGroup("Relay-API", prefix_group_id=True) as api:
        QualityAlertApiDummy = PythonOperator(
            task_id="QualityAlertApiDummy",
            python_callable=run_etl,
            params={
                "needs": QualityAlertApiDummy_task_config.needs,
                "prefers": QualityAlertApiDummy_task_config.prefers,
            },
            op_kwargs={
                "etl_name": "QualityAlertApiDummy",
                "resources": QualityAlertApiDummy_resources.resources,
            },
        )

    # --- Dynamic dependency wiring from task configs ---
    etl_ops = {
        "AssetInventorySnapshot": AssetInventorySnapshot,
        "SchemaComplianceChecker": SchemaComplianceChecker,
        "FieldFrequencyProfiler": FieldFrequencyProfiler,
        "CrossTeamJoinAuditor": CrossTeamJoinAuditor,
        "ComplianceMetricsPivot": ComplianceMetricsPivot,
        "AnomalyPatternMiner": AnomalyPatternMiner,
        "DataQualityScorecard": DataQualityScorecard,
        "QualityAlertApiDummy": QualityAlertApiDummy,
    }
    task_cfgs = {
        "AssetInventorySnapshot": AssetInventorySnapshot_task_config,
        "SchemaComplianceChecker": SchemaComplianceChecker_task_config,
        "FieldFrequencyProfiler": FieldFrequencyProfiler_task_config,
        "CrossTeamJoinAuditor": CrossTeamJoinAuditor_task_config,
        "ComplianceMetricsPivot": ComplianceMetricsPivot_task_config,
        "AnomalyPatternMiner": AnomalyPatternMiner_task_config,
        "DataQualityScorecard": DataQualityScorecard_task_config,
        "QualityAlertApiDummy": QualityAlertApiDummy_task_config,
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
