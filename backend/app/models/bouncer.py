"""Bouncer model — represents data-ingestion root tasks discovered from Airflow."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Bouncer(Base):
    __tablename__ = "bouncers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    bouncer_name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    team: Mapped[str | None] = mapped_column(String(100), index=True)
    volume_per_day: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[str | None] = mapped_column(String(50))
    dag_ids: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
