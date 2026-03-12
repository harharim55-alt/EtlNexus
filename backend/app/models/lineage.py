import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LineageEdge(Base):
    __tablename__ = "lineage_edges"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    source_pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipelines.id", ondelete="SET NULL"), index=True
    )
    target_pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipelines.id", ondelete="SET NULL"), index=True
    )
    source_table: Mapped[str] = mapped_column(String(500))
    target_table: Mapped[str] = mapped_column(String(500))
    edge_type: Mapped[str] = mapped_column(String(20))  # "reads_from" | "writes_to"
    discovered_at: Mapped[datetime] = mapped_column(server_default=func.now())

    source_pipeline: Mapped["Pipeline | None"] = relationship(
        foreign_keys=[source_pipeline_id], back_populates="lineage_targets"
    )
    target_pipeline: Mapped["Pipeline | None"] = relationship(
        foreign_keys=[target_pipeline_id], back_populates="lineage_sources"
    )


from app.models.pipeline import Pipeline  # noqa: E402, F401
