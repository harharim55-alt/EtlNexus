"""Pre-create the teams named in SYSTEM_TEAMS on startup."""

import logging

from app.config import configured_team_names
from app.database import async_session_factory
from app.repositories.team_repo import TeamRepository

logger = logging.getLogger(__name__)


async def seed_teams() -> None:
    """Pre-create the teams named in SYSTEM_TEAMS so they appear before any login.

    No-op when SYSTEM_TEAMS is the ``["*"]`` wildcard — there teams are created
    on demand from Keycloak groups at login instead.
    """
    names = configured_team_names()
    if not names:
        return
    async with async_session_factory() as session:
        team_repo = TeamRepository(session)
        await team_repo.get_or_create_many(names, source="config")
        await session.commit()
        logger.info("Ensured %d configured teams exist: %s", len(names), ", ".join(names))
