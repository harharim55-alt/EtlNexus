"""VisibilityGrant model — grants a team or user access to a specific pipeline or all pipelines owned by a team.

Exactly one of pipeline_id or source_team_id must be set per row (target).
Exactly one of grantee_team_id or grantee_user_id must be set per row (recipient).
Both constraints are enforced by CHECK constraints.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class VisibilityGrant(Base):
    __tablename__ = "visibility_grants"
    __table_args__ = (
        CheckConstraint(
            "(pipeline_id IS NOT NULL AND source_team_id IS NULL) OR "
            "(pipeline_id IS NULL AND source_team_id IS NOT NULL)",
            name="ck_visibility_grant_target",
        ),
        CheckConstraint(
            "(grantee_team_id IS NOT NULL AND grantee_user_id IS NULL) OR "
            "(grantee_team_id IS NULL AND grantee_user_id IS NOT NULL)",
            name="ck_visibility_grant_grantee",
        ),
        CheckConstraint(
            "grant_level IN ('viewer', 'editor')",
            name="ck_visibility_grants_grant_level",
        ),
        UniqueConstraint(
            "grantee_team_id",
            "grantee_user_id",
            "pipeline_id",
            "source_team_id",
            name="uq_visibility_grant_target_grantee",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    grantee_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"), index=True
    )
    grantee_user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    pipeline_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("pipelines.id", ondelete="CASCADE")
    )
    source_team_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE")
    )
    grant_level: Mapped[str] = mapped_column(String(20), default="viewer")
    granted_by: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    grantee_team: Mapped["Team"] = relationship(foreign_keys=[grantee_team_id])
    grantee_user: Mapped["User"] = relationship(foreign_keys=[grantee_user_id])
