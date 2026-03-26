"""DAG task graph — caches Airflow DAG membership and task dependency data."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint, func
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
    bouncer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    bouncer_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("bouncers.id", ondelete="SET NULL"), index=True, nullable=True
    )
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    pipeline: Mapped["Pipeline | None"] = relationship(foreign_keys=[pipeline_id])
    bouncer: Mapped["Bouncer | None"] = relationship(foreign_keys=[bouncer_id])


from app.models.bouncer import Bouncer  # noqa: E402, F401
from app.models.pipeline import Pipeline  # noqa: E402, F401
