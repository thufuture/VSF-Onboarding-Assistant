"""`/api/v1/admin/*`: quản trị hệ thống — chỉ ADMIN (người dùng, phòng ban, thành viên, lộ trình mẫu, nhật ký)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, require_role
from src.dto.request.admin_request_dto import (
    CreateMembershipRequestDTO,
    CreateTeamRequestDTO,
    CreateUserRequestDTO,
    SetTeamStatusRequestDTO,
    SetUserStatusRequestDTO,
    UpdateTeamRequestDTO,
    UpdateUserRequestDTO,
)
from src.dto.response.admin_response_dto import (
    AdminAuditLogResponseDTO,
    AdminDashboardResponseDTO,
    AdminMembershipResponseDTO,
    AdminTeamResponseDTO,
    AdminTemplateOverviewResponseDTO,
    AdminUserResponseDTO,
    AdminUserSecretResponseDTO,
)
from src.model.enums import UserRole
from src.model.user import User
from src.services.portal import admin_service

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/dashboard", response_model=AdminDashboardResponseDTO)
async def dashboard(user: AdminUser, db: Db) -> AdminDashboardResponseDTO:
    return await admin_service.get_dashboard(db)


@router.get("/users")
async def list_users(user: AdminUser, db: Db) -> list[AdminUserResponseDTO]:
    return await admin_service.list_users(db)


@router.post("/users", response_model=AdminUserSecretResponseDTO, status_code=201)
async def create_user(body: CreateUserRequestDTO, user: AdminUser, db: Db) -> AdminUserSecretResponseDTO:
    created, temp = await admin_service.create_user(
        db, user, display_name=body.display_name, email=body.email, role=body.role, team_id=body.team_id
    )
    return AdminUserSecretResponseDTO(user=created, temporary_password=temp)


@router.patch("/users/{user_id}", response_model=AdminUserResponseDTO)
async def update_user(user_id: int, body: UpdateUserRequestDTO, user: AdminUser, db: Db) -> AdminUserResponseDTO:
    return await admin_service.update_user(
        db, user, user_id, display_name=body.display_name, email=body.email, role=body.role
    )


@router.post("/users/{user_id}/reset-password", response_model=AdminUserSecretResponseDTO)
async def reset_password(user_id: int, user: AdminUser, db: Db) -> AdminUserSecretResponseDTO:
    target, temp = await admin_service.reset_password(db, user, user_id)
    return AdminUserSecretResponseDTO(user=target, temporary_password=temp)


@router.patch("/users/{user_id}/status", response_model=AdminUserResponseDTO)
async def set_user_status(user_id: int, body: SetUserStatusRequestDTO, user: AdminUser, db: Db) -> AdminUserResponseDTO:
    return await admin_service.set_user_status(db, user, user_id, body.status)


@router.get("/teams")
async def list_teams(user: AdminUser, db: Db) -> list[AdminTeamResponseDTO]:
    return await admin_service.list_teams(db)


@router.post("/teams", response_model=AdminTeamResponseDTO, status_code=201)
async def create_team(body: CreateTeamRequestDTO, user: AdminUser, db: Db) -> AdminTeamResponseDTO:
    return await admin_service.create_team(
        db,
        user,
        name=body.name,
        code=body.code,
        hr_user_id=body.hr_user_id,
        copy_shared_template=body.copy_shared_template,
    )


@router.patch("/teams/{team_id}", response_model=AdminTeamResponseDTO)
async def update_team(team_id: int, body: UpdateTeamRequestDTO, user: AdminUser, db: Db) -> AdminTeamResponseDTO:
    return await admin_service.update_team(db, user, team_id, name=body.name, hr_user_id=body.hr_user_id)


@router.patch("/teams/{team_id}/status", response_model=AdminTeamResponseDTO)
async def set_team_status(team_id: int, body: SetTeamStatusRequestDTO, user: AdminUser, db: Db) -> AdminTeamResponseDTO:
    return await admin_service.set_team_status(db, user, team_id, body.is_active)


@router.post("/teams/{team_id}/copy-template", response_model=AdminTeamResponseDTO)
async def copy_template(team_id: int, user: AdminUser, db: Db) -> AdminTeamResponseDTO:
    return await admin_service.copy_shared_template_to_team(db, user, team_id)


@router.get("/memberships")
async def list_memberships(user: AdminUser, db: Db) -> list[AdminMembershipResponseDTO]:
    return await admin_service.list_memberships(db)


@router.post("/memberships", status_code=204)
async def add_membership(body: CreateMembershipRequestDTO, user: AdminUser, db: Db) -> Response:
    await admin_service.add_membership(db, user, team_id=body.team_id, user_id=body.user_id)
    return Response(status_code=204)


@router.delete("/memberships/{team_id}/{user_id}", status_code=204)
async def remove_membership(team_id: int, user_id: int, user: AdminUser, db: Db) -> Response:
    await admin_service.remove_membership(db, user, team_id=team_id, user_id=user_id)
    return Response(status_code=204)


@router.get("/template-overview", response_model=AdminTemplateOverviewResponseDTO)
async def template_overview(user: AdminUser, db: Db) -> AdminTemplateOverviewResponseDTO:
    return await admin_service.template_overview(db)


@router.get("/audit-logs")
async def list_audit_logs(
    user: AdminUser, db: Db, limit: Annotated[int, Query(ge=1, le=200)] = 100
) -> list[AdminAuditLogResponseDTO]:
    return await admin_service.list_audit_logs(db, limit=limit)
