"""DAG task graph — caches Airflow DAG membership and task dependency data."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DagTask(Base):
    __tablename__ = "dag_tasks"
    __table_args__ = (
        UniqueConstraint("dag_id", "task_id", name="uq_dag_task"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    dag_id: Mapped[str] = mapped_column(String(255), index=True)
    task_id: Mapped[str] = mapped_column(String(255), index=True)
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipelines.id", ondelete="SET NULL"), index=True
    )
    downstream_task_ids: Mapped[list] = mapped_column(JSON, default=list)
    needs: Mapped[list] = mapped_column(JSON, default=list)
    prefers: Mapped[list] = mapped_column(JSON, default=list)
    task_group_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sensor_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sensor_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sensors.id", ondelete="SET NULL"), index=True, nullable=True
    )
    synced_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

    pipeline: Mapped["Pipeline | None"] = relationship(foreign_keys=[pipeline_id])
    sensor: Mapped["Sensor | None"] = relationship(foreign_keys=[sensor_id])


from app.models.pipeline import Pipeline  # noqa: E402, F401
from app.models.sensor import Sensor  # noqa: E402, F401
