"""Feature flag model — controls access to beta features like DAG dashboard and Bouncer dashboard."""

import uuid

from sqlalchemy import Boolean, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    beta_only: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    description: Mapped[str | None] = mapped_column(Text)
