import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineUsage(Base):
    __tablename__ = "pipeline_usages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    consumer_name: Mapped[str] = mapped_column(String(255))
    usage_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text)
    last_accessed_at: Mapped[datetime | None] = mapped_column()
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=func.now())

    pipeline: Mapped["Pipeline"] = relationship(back_populates="usages")


from app.models.pipeline import Pipeline  # noqa: E402, F401
