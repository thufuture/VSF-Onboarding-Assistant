from datetime import datetime

from pydantic import BaseModel


class AdminUserResponseDTO(BaseModel):
    id: int
    display_name: str
    email: str
    role: str
    status: str
    last_login_at: datetime | None
    team_names: list[str]


class AdminUserSecretResponseDTO(BaseModel):
    """Trả kèm mật khẩu tạm đúng một lần (lúc tạo / đặt lại); không lưu dạng đọc được."""

    user: AdminUserResponseDTO
    temporary_password: str


class AdminTeamResponseDTO(BaseModel):
    id: int
    code: str
    name: str
    is_active: bool
    created_at: datetime
    hr_names: list[str]
    hr_user_ids: list[int]
    employee_count: int
    hr_count: int
    journey_title: str | None
    journey_version: int | None
    journey_status: str | None


class AdminMembershipResponseDTO(BaseModel):
    team_id: int
    team_name: str
    user_id: int
    user_name: str
    user_email: str
    user_role: str
    team_role: str
    access: str
    joined_at: datetime


class AdminAuditLogResponseDTO(BaseModel):
    id: int
    created_at: datetime
    actor_name: str | None
    action: str
    entity_type: str
    entity_id: str
    target: str | None


class AdminDashboardResponseDTO(BaseModel):
    active_teams: int
    archived_teams: int
    hr_count: int
    employee_count: int
    employees_without_team: int
    inactive_users: int
    employees_by_team: list[tuple[str, int]]
    recent_logs: list[AdminAuditLogResponseDTO]


class AdminTemplateOverviewResponseDTO(BaseModel):
    shared_template_id: int | None
    shared_title: str | None
    shared_version: int | None
    shared_status: str | None
    shared_task_count: int
    teams_using_copy: int
    active_teams: int
