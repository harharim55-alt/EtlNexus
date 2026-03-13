"""Team endpoints — list, detail, and per-team pipeline views."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user
from app.dependencies import get_team_service
from app.models.user import User
from app.models.user_team import UserTeam
from app.schemas.team import TeamDetailResponse, TeamMemberInfo, TeamResponse
from app.schemas.pipeline import PipelineListItem
from app.services.team_service import TeamService

router = APIRouter(prefix="/api/teams", tags=["teams"])


@router.get("", response_model=list[TeamResponse])
async def list_teams(
    user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> list[TeamResponse]:
    """List all teams with member counts.

    Args:
        user: Authenticated caller (any role may list teams).
        service: Injected TeamService.

    Returns:
        Ordered list of teams with member counts.
    """
    teams = await service.list_teams()
    return [
        TeamResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            source=t.source,
            member_count=len(t.members) if t.members else 0,
        )
        for t in teams
    ]


@router.get("/{team_id}", response_model=TeamDetailResponse)
async def get_team(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> TeamDetailResponse:
    """Get team details including full member list.

    Args:
        team_id: UUID of the team to retrieve.
        user: Authenticated caller.
        service: Injected TeamService.

    Returns:
        Team record with members eagerly loaded.

    Raises:
        HTTPException(404): When no team with the given ID exists.
    """
    team = await service.get_team_detail(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Restrict full member details to admins and same-team members
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
    if user.role != "admin" and team_id not in user_team_ids:
        raise HTTPException(
            status_code=403,
            detail="Access restricted to team members and admins",
        )

    members = [
        TeamMemberInfo(
            id=ut.user.id if ut.user else ut.user_id,
            email=ut.user.email if ut.user else "",
            display_name=ut.user.display_name if ut.user else "",
            role=ut.user.role if ut.user else "member",
            role_in_team=ut.role_in_team,
        )
        for ut in (team.members or [])
        if isinstance(ut, UserTeam)
    ]

    return TeamDetailResponse(
        id=team.id,
        name=team.name,
        description=team.description,
        source=team.source,
        members=members,
    )


@router.get("/{team_id}/pipelines", response_model=list[PipelineListItem])
async def get_team_pipelines(
    team_id: uuid.UUID,
    user: User = Depends(get_current_user),
    service: TeamService = Depends(get_team_service),
) -> list[PipelineListItem]:
    """List pipelines owned by this team.

    Args:
        team_id: UUID of the owning team.
        user: Authenticated caller.
        service: Injected TeamService.

    Returns:
        List of pipeline summaries belonging to the team.

    Raises:
        HTTPException(404): When no team with the given ID exists.
    """
    team = await service.get_team_detail(team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    # Restrict to admins and same-team members
    user_team_ids = {ut.team_id for ut in (user.team_memberships or [])}
    if user.role != "admin" and team_id not in user_team_ids:
        raise HTTPException(
            status_code=403,
            detail="Access restricted to team members and admins",
        )

    pipelines = await service.get_team_pipelines(team_id)
    return [
        PipelineListItem(
            id=p.id,
            name=p.name,
            description=p.description,
            category=p.category,
            schedule=p.schedule,
            rows_per_day=p.rows_per_day,
            airflow_status=(
                p.airflow_status.status if p.airflow_status else "unknown"
            ),
            team=p.team,
        )
        for p in pipelines
    ]
