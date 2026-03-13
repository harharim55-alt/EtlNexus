"""Reusable FastAPI dependency for optional date range query parameters."""

from datetime import datetime

from fastapi import Query


class DateRangeParams:
    """Inject as Depends() to accept optional date_from / date_to query params."""

    def __init__(
        self,
        date_from: datetime | None = Query(None, description="Start of range (ISO 8601 UTC)"),
        date_to: datetime | None = Query(None, description="End of range (ISO 8601 UTC)"),
    ):
        self.date_from = date_from
        self.date_to = date_to
