import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    task_id: Mapped[str | None] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str | None] = mapped_column(String(100))
    schedule: Mapped[str | None] = mapped_column(String(100))
    rows_per_day: Mapped[str | None] = mapped_column(String(50))
    documentation: Mapped[str | None] = mapped_column(Text)
    last_updated_by: Mapped[str | None] = mapped_column(String(255))
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    fields: Mapped[list["PipelineField"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan", order_by="PipelineField.ordinal_position"
    )
    airflow_status: Mapped["AirflowRunStatus | None"] = relationship(
        back_populates="pipeline", uselist=False
    )
    # Lineage: edges where this pipeline is the target (reads from)
    lineage_sources: Mapped[list["LineageEdge"]] = relationship(
        foreign_keys="LineageEdge.target_pipeline_id", back_populates="target_pipeline"
    )
    # Lineage: edges where this pipeline is the source (writes to)
    lineage_targets: Mapped[list["LineageEdge"]] = relationship(
        foreign_keys="LineageEdge.source_pipeline_id", back_populates="source_pipeline"
    )
    resource_configs: Mapped[list["PipelineResourceConfig"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )
    run_history: Mapped[list["PipelineRunHistory"]] = relationship(
        back_populates="pipeline", cascade="all, delete-orphan"
    )


class PipelineField(Base):
    __tablename__ = "pipeline_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), index=True)
    data_type: Mapped[str | None] = mapped_column(String(50))
    ordinal_position: Mapped[int] = mapped_column(default=0)

    pipeline: Mapped["Pipeline"] = relationship(back_populates="fields")


# Avoid circular import issues — these are imported at module level by __init__.py
from app.models.airflow_status import AirflowRunStatus  # noqa: E402, F401
from app.models.lineage import LineageEdge  # noqa: E402, F401
from app.models.resource_config import PipelineResourceConfig  # noqa: E402, F401
from app.models.run_history import PipelineRunHistory  # noqa: E402, F401
