"""Team model — represents an organizational team for pipeline ownership and access control."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(50), default="sso")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    members: Mapped[list["UserTeam"]] = relationship(
        back_populates="team", cascade="all, delete-orphan"
    )
