import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class PipelineRevision(Base):
    __tablename__ = "pipeline_revisions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String(50))
    content: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(255))
    change_source: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    pipeline: Mapped["Pipeline"] = relationship()


from app.models.pipeline import Pipeline  # noqa: E402
