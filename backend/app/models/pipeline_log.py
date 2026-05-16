"""Pipeline log models — multiple named logs per pipeline, each with per-network schema and retention."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineLog(Base):
    __tablename__ = "pipeline_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="logs")
    networks: Mapped[list["PipelineLogNetwork"]] = relationship(
        back_populates="log", cascade="all, delete-orphan"
    )
    fields: Mapped[list["PipelineLogField"]] = relationship(
        back_populates="log", cascade="all, delete-orphan", order_by="PipelineLogField.ordinal_position"
    )


class PipelineLogNetwork(Base):
    __tablename__ = "pipeline_log_networks"
    __table_args__ = (
        UniqueConstraint("log_id", "network_id", name="uq_log_network"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_logs.id", ondelete="CASCADE"), index=True
    )
    network_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("networks.id", ondelete="CASCADE"), index=True
    )
    retention: Mapped[str | None] = mapped_column(String(100))

    log: Mapped["PipelineLog"] = relationship(back_populates="networks")
    network: Mapped["Network"] = relationship()


class PipelineLogField(Base):
    __tablename__ = "pipeline_log_fields"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    log_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipeline_logs.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    data_type: Mapped[str | None] = mapped_column(String(50))
    ordinal_position: Mapped[int] = mapped_column(Integer, default=0)

    log: Mapped["PipelineLog"] = relationship(back_populates="fields")


from app.models.network import Network  # noqa: E402
from app.models.pipeline import Pipeline  # noqa: E402
