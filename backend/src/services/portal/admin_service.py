"""Quản trị hệ thống (ADMIN): người dùng, phòng ban (`teams`), thành viên (`team_members`), sao lộ trình mẫu, nhật ký.

Không thêm bảng mới: phòng ban = `teams`, vai trò trong phòng ban suy ra từ vai trò hệ thống (HR → HR phụ trách,
USER → nhân viên mới), truy cập đóng khi tài khoản INACTIVE hoặc phòng ban lưu trữ. Mọi thay đổi ghi `audit_logs`.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dto.response.admin_response_dto import (
    AdminAuditLogResponseDTO,
    AdminDashboardResponseDTO,
    AdminMembershipResponseDTO,
    AdminTeamResponseDTO,
    AdminTemplateOverviewResponseDTO,
    AdminUserResponseDTO,
)
from src.model.audit_log import AuditLog
from src.model.enums import JourneyTemplateStatus, StageVersionStatus, UserRole, UserStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
from src.model.task_dependency import TaskDependency
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.passwords import hash_password
from src.services.portal import stage_version_service
from src.services.portal.errors import PortalError


async def _audit(
    session: AsyncSession, actor: User, action: str, entity_type: str, entity_id: int | str, **after: Any
) -> None:
    session.add(
        AuditLog(actor_id=actor.id, action=action, entity_type=entity_type, entity_id=str(entity_id), after=after)
    )


def _temp_password() -> str:
    return secrets.token_urlsafe(9)


# ── Người dùng ──────────────────────────────────────────────────────────────


async def _user_dto(session: AsyncSession, user: User) -> AdminUserResponseDTO:
    names = (
        await session.scalars(
            select(Team.name)
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(TeamMember.user_id == user.id)
            .order_by(Team.name)
        )
    ).all()
    return AdminUserResponseDTO(
        id=user.id,
        display_name=user.display_name,
        email=user.email,
        role=user.role,
        status=user.status,
        last_login_at=user.last_login_at,
        team_names=list(names),
    )


async def list_users(session: AsyncSession) -> list[AdminUserResponseDTO]:
    users = (await session.scalars(select(User).order_by(User.role, User.display_name))).all()
    return [await _user_dto(session, u) for u in users]


async def _get_user(session: AsyncSession, user_id: int) -> User:
    user = await session.get(User, user_id)
    if user is None:
        raise PortalError(404, "USER_NOT_FOUND", "admin.user_not_found")
    return user


async def _ensure_email_free(session: AsyncSession, email: str, *, except_id: int | None = None) -> None:
    query = select(User.id).where(func.lower(User.email) == email.lower())
    if except_id is not None:
        query = query.where(User.id != except_id)
    if await session.scalar(query) is not None:
        raise PortalError(409, "EMAIL_TAKEN", "admin.email_taken")


async def create_user(
    session: AsyncSession, actor: User, *, display_name: str, email: str, role: str, team_id: int | None
) -> tuple[AdminUserResponseDTO, str]:
    await _ensure_email_free(session, email)
    if team_id is not None:
        await _get_team(session, team_id)
    temp = _temp_password()
    user = User(
        email=email.strip(),
        display_name=display_name.strip(),
        password_hash=hash_password(temp),
        role=role,
        status=UserStatus.ACTIVE.value,
        must_change_password=True,
        created_by=actor.id,
    )
    session.add(user)
    await session.flush()
    if team_id is not None and role != UserRole.ADMIN:
        session.add(TeamMember(team_id=team_id, user_id=user.id))
    await _audit(session, actor, "CREATE_USER", "user", user.id, email=user.email, role=role)
    await session.commit()
    return await _user_dto(session, user), temp


async def update_user(
    session: AsyncSession, actor: User, user_id: int, *, display_name: str, email: str, role: str
) -> AdminUserResponseDTO:
    user = await _get_user(session, user_id)
    await _ensure_email_free(session, email, except_id=user.id)
    if user.id == actor.id and role != UserRole.ADMIN:
        raise PortalError(409, "CANNOT_DEMOTE_SELF", "admin.cannot_demote_self")
    changed_role = user.role != role
    user.display_name = display_name.strip()
    user.email = email.strip()
    user.role = role
    if changed_role:
        # Đổi vai trò thì thu hồi phiên cũ để quyền mới có hiệu lực ngay.
        user.session_invalid_before = datetime.now(UTC)
    await _audit(session, actor, "UPDATE_USER", "user", user.id, email=user.email, role=role)
    await session.commit()
    return await _user_dto(session, user)


async def reset_password(session: AsyncSession, actor: User, user_id: int) -> tuple[AdminUserResponseDTO, str]:
    user = await _get_user(session, user_id)
    temp = _temp_password()
    user.password_hash = hash_password(temp)
    user.must_change_password = True
    user.session_invalid_before = datetime.now(UTC)
    await _audit(session, actor, "RESET_PASSWORD", "user", user.id)
    await session.commit()
    return await _user_dto(session, user), temp


async def set_user_status(session: AsyncSession, actor: User, user_id: int, status: str) -> AdminUserResponseDTO:
    user = await _get_user(session, user_id)
    if user.id == actor.id and status != UserStatus.ACTIVE:
        raise PortalError(409, "CANNOT_LOCK_SELF", "admin.cannot_lock_self")
    user.status = status
    if status != UserStatus.ACTIVE:
        user.session_invalid_before = datetime.now(UTC)
    await _audit(session, actor, "LOCK_USER" if status != UserStatus.ACTIVE else "UNLOCK_USER", "user", user.id)
    await session.commit()
    return await _user_dto(session, user)


# ── Phòng ban ───────────────────────────────────────────────────────────────


async def _get_team(session: AsyncSession, team_id: int) -> Team:
    team = await session.get(Team, team_id)
    if team is None:
        raise PortalError(404, "TEAM_NOT_FOUND", "admin.team_not_found")
    return team


async def _team_dto(session: AsyncSession, team: Team) -> AdminTeamResponseDTO:
    members = (
        await session.execute(
            select(User.id, User.display_name, User.role)
            .join(TeamMember, TeamMember.user_id == User.id)
            .where(TeamMember.team_id == team.id)
            .order_by(User.display_name)
        )
    ).all()
    hrs = [(uid, name) for uid, name, role in members if role == UserRole.HR]
    journey = await session.scalar(
        select(JourneyTemplate)
        .where(JourneyTemplate.team_id == team.id)
        .order_by(JourneyTemplate.status.desc(), JourneyTemplate.version.desc(), JourneyTemplate.id.desc())
        .limit(1)
    )
    return AdminTeamResponseDTO(
        id=team.id,
        code=team.code,
        name=team.name,
        is_active=team.is_active,
        created_at=team.created_at,
        hr_names=[name for _, name in hrs],
        hr_user_ids=[uid for uid, _ in hrs],
        employee_count=sum(1 for _, _, role in members if role == UserRole.USER),
        hr_count=len(hrs),
        journey_title=journey.title if journey else None,
        journey_version=journey.version if journey else None,
        journey_status=journey.status if journey else None,
    )


async def list_teams(session: AsyncSession) -> list[AdminTeamResponseDTO]:
    teams = (await session.scalars(select(Team).order_by(Team.is_active.desc(), Team.name))).all()
    return [await _team_dto(session, t) for t in teams]


async def _ensure_hr(session: AsyncSession, hr_user_id: int) -> None:
    role = await session.scalar(select(User.role).where(User.id == hr_user_id))
    if role != UserRole.HR:
        raise PortalError(422, "NOT_AN_HR_USER", "admin.not_an_hr_user")


async def _add_member(session: AsyncSession, team_id: int, user_id: int) -> None:
    if await session.get(TeamMember, (team_id, user_id)) is None:
        session.add(TeamMember(team_id=team_id, user_id=user_id))


async def create_team(
    session: AsyncSession,
    actor: User,
    *,
    name: str,
    code: str,
    hr_user_id: int | None,
    copy_shared_template: bool,
) -> AdminTeamResponseDTO:
    if await session.scalar(select(Team.id).where(Team.code == code)) is not None:
        raise PortalError(409, "TEAM_CODE_TAKEN", "admin.team_code_taken")
    if hr_user_id is not None:
        await _ensure_hr(session, hr_user_id)
    team = Team(code=code, name=name.strip())
    session.add(team)
    await session.flush()
    if hr_user_id is not None:
        await _add_member(session, team.id, hr_user_id)
    if copy_shared_template:
        await _copy_shared_template(session, actor, team, must_exist=False)
    await _audit(session, actor, "CREATE_TEAM", "team", team.id, name=team.name, code=code)
    await session.commit()
    return await _team_dto(session, team)


async def update_team(
    session: AsyncSession, actor: User, team_id: int, *, name: str, hr_user_id: int | None
) -> AdminTeamResponseDTO:
    team = await _get_team(session, team_id)
    team.name = name.strip()
    if hr_user_id is not None:
        await _ensure_hr(session, hr_user_id)
        await _add_member(session, team.id, hr_user_id)
    await _audit(session, actor, "UPDATE_TEAM", "team", team.id, name=team.name)
    await session.commit()
    return await _team_dto(session, team)


async def set_team_status(session: AsyncSession, actor: User, team_id: int, is_active: bool) -> AdminTeamResponseDTO:
    team = await _get_team(session, team_id)
    team.is_active = is_active
    await _audit(session, actor, "RESTORE_TEAM" if is_active else "ARCHIVE_TEAM", "team", team.id, name=team.name)
    await session.commit()
    return await _team_dto(session, team)


# ── Thành viên ──────────────────────────────────────────────────────────────


def _access(user_status: str, team_active: bool) -> str:
    if not team_active:
        return "BLOCKED_TEAM"
    if user_status != UserStatus.ACTIVE:
        return "BLOCKED_USER"
    return "ACTIVE"


async def list_memberships(session: AsyncSession) -> list[AdminMembershipResponseDTO]:
    rows = (
        await session.execute(
            select(TeamMember, Team, User)
            .join(Team, Team.id == TeamMember.team_id)
            .join(User, User.id == TeamMember.user_id)
            .order_by(Team.name, User.display_name)
        )
    ).all()
    return [
        AdminMembershipResponseDTO(
            team_id=team.id,
            team_name=team.name,
            user_id=user.id,
            user_name=user.display_name,
            user_email=user.email,
            user_role=user.role,
            team_role="HR" if user.role == UserRole.HR else "EMPLOYEE",
            access=_access(user.status, team.is_active),
            joined_at=member.created_at,
        )
        for member, team, user in rows
    ]


async def add_membership(session: AsyncSession, actor: User, *, team_id: int, user_id: int) -> None:
    team = await _get_team(session, team_id)
    user = await _get_user(session, user_id)
    if user.role == UserRole.ADMIN:
        raise PortalError(422, "ADMIN_HAS_NO_TEAM", "admin.admin_has_no_team")
    if await session.get(TeamMember, (team_id, user_id)) is not None:
        raise PortalError(409, "ALREADY_MEMBER", "admin.already_member")
    session.add(TeamMember(team_id=team_id, user_id=user_id))
    await _audit(session, actor, "ADD_MEMBER", "team", team.id, user=user.display_name)
    await session.commit()


async def remove_membership(session: AsyncSession, actor: User, *, team_id: int, user_id: int) -> None:
    member = await session.get(TeamMember, (team_id, user_id))
    if member is None:
        raise PortalError(404, "MEMBERSHIP_NOT_FOUND", "admin.membership_not_found")
    team = await _get_team(session, team_id)
    user = await _get_user(session, user_id)
    await session.delete(member)
    await _audit(session, actor, "REMOVE_MEMBER", "team", team.id, user=user.display_name)
    await session.commit()


# ── Lộ trình mẫu chung ──────────────────────────────────────────────────────


async def _shared_template(session: AsyncSession) -> JourneyTemplate | None:
    result: JourneyTemplate | None = await session.scalar(
        select(JourneyTemplate)
        .where(JourneyTemplate.team_id.is_(None), JourneyTemplate.status == JourneyTemplateStatus.PUBLISHED)
        .order_by(JourneyTemplate.version.desc(), JourneyTemplate.id.desc())
        .limit(1)
    )
    return result


async def template_overview(session: AsyncSession) -> AdminTemplateOverviewResponseDTO:
    shared = await _shared_template(session)
    task_count = 0
    if shared is not None:
        task_count = (
            await session.scalar(
                select(func.count(TaskTemplate.id))
                .join(StageVersion, StageVersion.id == TaskTemplate.stage_version_id)
                .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
                .where(
                    JourneyStage.journey_template_id == shared.id,
                    StageVersion.status == StageVersionStatus.APPLIED.value,
                )
            )
            or 0
        )
    active_teams = await session.scalar(select(func.count(Team.id)).where(Team.is_active.is_(True))) or 0
    using = (
        await session.scalar(
            select(func.count(func.distinct(JourneyTemplate.team_id)))
            .join(Team, Team.id == JourneyTemplate.team_id)
            .where(Team.is_active.is_(True))
        )
        or 0
    )
    return AdminTemplateOverviewResponseDTO(
        shared_template_id=shared.id if shared else None,
        shared_title=shared.title if shared else None,
        shared_version=shared.version if shared else None,
        shared_status=shared.status if shared else None,
        shared_task_count=task_count,
        teams_using_copy=using,
        active_teams=active_teams,
    )


async def _copy_shared_template(session: AsyncSession, actor: User, team: Team, *, must_exist: bool) -> None:
    shared = await _shared_template(session)
    if shared is None:
        if must_exist:
            raise PortalError(409, "NO_SHARED_TEMPLATE", "admin.no_shared_template")
        return
    if await session.scalar(select(JourneyTemplate.id).where(JourneyTemplate.team_id == team.id).limit(1)) is not None:
        raise PortalError(409, "TEAM_ALREADY_HAS_JOURNEY", "admin.team_already_has_journey")
    copy = JourneyTemplate(
        code=f"{shared.code}-{team.code.lower()}",
        version=1,
        title=shared.title,
        description=shared.description,
        status=JourneyTemplateStatus.DRAFT.value,
        team_id=team.id,
        created_by=actor.id,
    )
    session.add(copy)
    await session.flush()
    task_map: dict[int, int] = {}
    stages = (
        await session.scalars(
            select(JourneyStage).where(JourneyStage.journey_template_id == shared.id).order_by(JourneyStage.sort_order)
        )
    ).all()
    for stage in stages:
        new_stage = JourneyStage(journey_template_id=copy.id, title=stage.title, sort_order=stage.sort_order)
        session.add(new_stage)
        await session.flush()
        # Bản sao nhận v1 ở trạng thái NHÁP (HR của team duyệt rồi mới áp dụng), nội dung lấy từ bản đang áp dụng của ngày chung.
        new_version = await stage_version_service.create_initial_version(session, new_stage, actor)
        applied = await session.scalar(
            select(StageVersion).where(
                StageVersion.journey_stage_id == stage.id, StageVersion.status == StageVersionStatus.APPLIED.value
            )
        )
        tasks = (
            (
                await session.scalars(
                    select(TaskTemplate)
                    .where(TaskTemplate.stage_version_id == applied.id)
                    .order_by(TaskTemplate.sort_order)
                )
            ).all()
            if applied is not None
            else []
        )
        for task in tasks:
            new_task = TaskTemplate(
                journey_stage_id=new_stage.id,
                stage_version_id=new_version.id,
                title=task.title,
                body_markdown=task.body_markdown,
                sort_order=task.sort_order,
                required=task.required,
                team_id=team.id,
            )
            session.add(new_task)
            await session.flush()
            task_map[task.id] = new_task.id
    if task_map:
        deps = (
            await session.scalars(select(TaskDependency).where(TaskDependency.task_template_id.in_(list(task_map))))
        ).all()
        for dep in deps:
            if dep.depends_on_task_template_id in task_map:
                session.add(
                    TaskDependency(
                        task_template_id=task_map[dep.task_template_id],
                        depends_on_task_template_id=task_map[dep.depends_on_task_template_id],
                    )
                )
    await _audit(session, actor, "COPY_TEMPLATE", "team", team.id, template=shared.title)


async def copy_shared_template_to_team(session: AsyncSession, actor: User, team_id: int) -> AdminTeamResponseDTO:
    team = await _get_team(session, team_id)
    await _copy_shared_template(session, actor, team, must_exist=True)
    await session.commit()
    return await _team_dto(session, team)


# ── Nhật ký + Tổng quan ─────────────────────────────────────────────────────


async def list_audit_logs(session: AsyncSession, *, limit: int) -> list[AdminAuditLogResponseDTO]:
    rows = (
        await session.execute(
            select(AuditLog, User.display_name)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
        )
    ).all()
    result: list[AdminAuditLogResponseDTO] = []
    for log, actor_name in rows:
        after = log.after or {}
        target = after.get("name") or after.get("user") or after.get("email") or after.get("template")
        result.append(
            AdminAuditLogResponseDTO(
                id=log.id,
                created_at=log.created_at,
                actor_name=actor_name,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                target=str(target) if target else None,
            )
        )
    return result


async def get_dashboard(session: AsyncSession) -> AdminDashboardResponseDTO:
    active = await session.scalar(select(func.count(Team.id)).where(Team.is_active.is_(True))) or 0
    archived = await session.scalar(select(func.count(Team.id)).where(Team.is_active.is_(False))) or 0
    hr = await session.scalar(select(func.count(User.id)).where(User.role == UserRole.HR)) or 0
    emp = await session.scalar(select(func.count(User.id)).where(User.role == UserRole.USER)) or 0
    no_team = (
        await session.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.USER, ~select(TeamMember.user_id).where(TeamMember.user_id == User.id).exists()
            )
        )
        or 0
    )
    inactive = await session.scalar(select(func.count(User.id)).where(User.status != UserStatus.ACTIVE)) or 0
    per_team = (
        await session.execute(
            select(Team.name, func.count(User.id))
            .outerjoin(TeamMember, TeamMember.team_id == Team.id)
            .outerjoin(User, (User.id == TeamMember.user_id) & (User.role == UserRole.USER))
            .where(Team.is_active.is_(True))
            .group_by(Team.id, Team.name)
            .order_by(Team.name)
        )
    ).all()
    return AdminDashboardResponseDTO(
        active_teams=active,
        archived_teams=archived,
        hr_count=hr,
        employee_count=emp,
        employees_without_team=no_team,
        inactive_users=inactive,
        employees_by_team=[(name, count) for name, count in per_team],
        recent_logs=await list_audit_logs(session, limit=5),
    )
