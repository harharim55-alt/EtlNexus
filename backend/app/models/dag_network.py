import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class DagNetwork(Base):
    __tablename__ = "dag_networks"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    network_name: Mapped[str] = mapped_column(String(255))
    last_synced_at: Mapped[datetime] = mapped_column(default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="dag_networks")
