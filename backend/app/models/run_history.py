import uuid
from datetime import datetime

from sqlalchemy import Float, ForeignKey, Integer, String, func, UniqueConstraint
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
    dag_id: Mapped[str] = mapped_column(String(255))
    dag_run_id: Mapped[str] = mapped_column(String(255))
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(String(50))
    driver_memory_used_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    executor_memory_peak_mb: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cpu_utilization_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    executors_active: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="run_history")


from app.models.pipeline import Pipeline  # noqa: E402, F401
