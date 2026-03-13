import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AirflowRunStatus(Base):
    __tablename__ = "airflow_run_statuses"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), unique=True
    )
    dag_id: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50))  # "success" | "failed" | "running" | "unknown"
    execution_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="airflow_status")


from app.models.pipeline import Pipeline  # noqa: E402, F401
