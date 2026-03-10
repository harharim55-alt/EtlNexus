import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineResourceConfig(Base):
    __tablename__ = "pipeline_resource_configs"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "dag_id", name="uq_resource_config_pipeline_dag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    dag_id: Mapped[str] = mapped_column(String(255))
    spark_driver_memory: Mapped[str | None] = mapped_column(String(20), nullable=True)
    spark_executor_memory: Mapped[str | None] = mapped_column(String(20), nullable=True)
    spark_executor_cores: Mapped[int | None] = mapped_column(Integer, nullable=True)
    spark_num_executors: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_dag_override: Mapped[bool] = mapped_column(Boolean, default=False)
    synced_at: Mapped[datetime] = mapped_column(default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="resource_configs")


from app.models.pipeline import Pipeline  # noqa: E402, F401
