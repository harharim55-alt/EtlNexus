"""TypedDicts for internal data structures crossing service/repository boundaries."""

import uuid
from datetime import datetime
from typing import NotRequired, TypedDict


class EdgeData(TypedDict, total=False):
    target_pipeline_id: uuid.UUID
    source_pipeline_id: uuid.UUID
    source_table: str
    target_table: str
    edge_type: str


class ResourceConfigData(TypedDict):
    pipeline_id: uuid.UUID
    dag_id: str
    spark_driver_memory: NotRequired[str | None]
    spark_executor_memory: NotRequired[str | None]
    spark_executor_cores: NotRequired[int | None]
    spark_num_executors: NotRequired[int | None]
    is_dag_override: bool
    synced_at: datetime


class PipelineUpsertData(TypedDict):
    name: str
    task_id: str
    description: str
    category: str | None
    schedule: str | None
