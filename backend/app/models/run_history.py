import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineRunHistory(Base):
    __tablename__ = "pipeline_run_history"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "dag_id", "dag_run_id", name="uq_run_history_pipeline_dag_run"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    dag_id: Mapped[str] = mapped_column(String(255), index=True)
    dag_run_id: Mapped[str] = mapped_column(String(255))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    driver_memory_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executor_memory_peak_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_utilization_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    executors_active: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # sparkMeasure / real Spark metrics (migration 012)
    spark_application_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    executor_run_time_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    executor_cpu_time_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    jvm_gc_time_ms: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shuffle_read_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    shuffle_write_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    input_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    output_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    memory_bytes_spilled: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    disk_bytes_spilled: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    peak_execution_memory: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    result_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    num_tasks: Mapped[int | None] = mapped_column(Integer, nullable=True)
    num_stages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    metrics_source: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Spark execution plan (migration 013)
    execution_plan: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Per-run snapshots of schema & lineage (migration 031)
    fields_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    source_tables_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)
    destination_tables_snapshot: Mapped[list | None] = mapped_column(JSON, nullable=True)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="run_history")


from app.models.pipeline import Pipeline  # noqa: E402
