"""Tag model — user-defined labels for pipeline categorization, replacing task groups."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    created_by_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by_team: Mapped["Team | None"] = relationship(foreign_keys=[created_by_team_id])
    pipeline_tags: Mapped[list["PipelineTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class PipelineTag(Base):
    __tablename__ = "pipeline_tags"
    __table_args__ = (
        UniqueConstraint("pipeline_id", "tag_id", name="uq_pipeline_tag"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    pipeline_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE"), index=True
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tags.id", ondelete="CASCADE"), index=True
    )

    pipeline: Mapped["Pipeline"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="pipeline_tags")


from app.models.pipeline import Pipeline  # noqa: E402
from app.models.team import Team  # noqa: E402
