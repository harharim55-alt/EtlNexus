"""Team endpoints — list, detail, and per-team pipeline views."""

import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.auth import get_current_user, require_team_admin
from app.dependencies import get_team_service
from app.models.user import User
from app.models.user_team import UserTeam
from app.schemas.common import SuccessResponse
from app.schemas.pipeline import PipelineListItem
from app.schemas.team import AddMemberRequest, TeamDetailResponse, TeamMemberInfo, TeamResponse
from app.services.team_service import TeamService
from app.services.user_auth_service import invalidate_user_cache

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
    if not service.user_can_access_team(user, team_id):
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
    if not service.user_can_access_team(user, team_id):
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
            schedule_type=p.schedule_type,
            team=p.team,
            is_data_product=p.is_data_product,
        )
        for p in pipelines
    ]


@router.post("/{team_id}/members", response_model=TeamMemberInfo, status_code=201)
async def add_team_member(
    team_id: uuid.UUID,
    body: AddMemberRequest,
    user: User = Depends(require_team_admin("team_id")),
    service: TeamService = Depends(get_team_service),
) -> TeamMemberInfo:
    """Add an existing user to a team by username (team-admin only).

    The target must have signed in at least once (so they exist in the system).
    """
    target = await service.add_member_by_username(team_id, body.username)
    if not target:
        raise HTTPException(
            status_code=404,
            detail=f"No user found for '{body.username}'. They must sign in once before being added.",
        )
    await service.team_repo.session.commit()
    await invalidate_user_cache()
    return TeamMemberInfo(
        id=target.id,
        email=target.email,
        display_name=target.display_name,
        role=target.role,
        role_in_team="member",
    )


@router.delete("/{team_id}/members/{user_id}", response_model=SuccessResponse)
async def remove_team_member(
    team_id: uuid.UUID,
    user_id: uuid.UUID,
    user: User = Depends(require_team_admin("team_id")),
    service: TeamService = Depends(get_team_service),
) -> SuccessResponse:
    """Remove a user from a team (team-admin only). Admins cannot remove themselves."""
    if user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself from the team")
    removed = await service.remove_member(team_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="User is not a member of this team")
    await service.team_repo.session.commit()
    await invalidate_user_cache()
    return SuccessResponse()
