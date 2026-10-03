"""`/api/v1/portal/*`: RBAC/scope mẫu + upload tài liệu + AI đề xuất task (plan-portal/P1, P4B).

Route journey/task thủ công đầy đủ (dependency, publish) chưa có ở đây — chỉ đủ để luồng
upload → AI đề xuất → accept chạy được end-to-end (P4B mục 8).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    get_chat_completion_port,
    get_current_user,
    get_db,
    require_role,
    require_team_scope,
    session_secret,
)
from src.api.routers.auth_router import set_session_cookie
from src.config import Settings, get_settings
from src.dto.request.portal_request_dto import (
    AcceptAiTaskProposalRequestDTO,
    ChangeMyPasswordRequestDTO,
    CreateAiTaskProposalRequestDTO,
    CreateJourneyStageRequestDTO,
    CreateJourneyTemplateRequestDTO,
    CreateTaskManualRequestDTO,
    SetDocumentStatusRequestDTO,
    UpdateDocumentRequestDTO,
    UpdateMyProfileRequestDTO,
    UpdateTaskTemplateRequestDTO,
)
from src.dto.response.portal_response_dto import (
    AiTaskProposalResponseDTO,
    DocumentCategoryResponseDTO,
    DocumentListItemResponseDTO,
    EmployeeDocumentResponseDTO,
    EmployeeJourneyResponseDTO,
    EmployeePrerequisiteResponseDTO,
    EmployeeProfileResponseDTO,
    EmployeeSummaryResponseDTO,
    EmployeeTaskResponseDTO,
    HrDashboardResponseDTO,
    JourneyStageResponseDTO,
    JourneyTemplateResponseDTO,
    StageNodeResponseDTO,
    StageOptionResponseDTO,
    TaskNodeResponseDTO,
    TaskSourceResponseDTO,
    TaskTemplateResponseDTO,
    TemplateNodeResponseDTO,
)
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.model.enums import DocumentStatus, UserRole
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.auth.auth_service import start_session
from src.services.auth.errors import AuthError
from src.services.portal import (
    ai_task_service,
    employee_service,
    journey_service,
    profile_service,
    task_sources,
    template_service,
)
from src.services.portal.errors import PortalError
from src.services.portal.ingest_bridge import resolve_original_document
from src.services.viga import snapshot as snapshot_service

router = APIRouter(prefix="/api/v1/portal", tags=["portal"])


@router.get("/journeys")
async def list_journeys(
    team_id: int,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, object]:
    await require_team_scope(team_id, user, db)
    return {"team_id": team_id, "journeys": []}


@router.get("/me")
async def portal_me(user: Annotated[User, Depends(get_current_user)]) -> dict[str, object]:
    """Mọi vai trò đăng nhập đều gọi được — không kiểm team_id vì chưa gắn resource cụ thể."""
    return {"user_id": user.id, "role": user.role}


async def _require_template_scope(db: AsyncSession, user: User, template_id: int) -> JourneyTemplate:
    template = await template_service.get_journey_template(db, template_id)
    await _check_template_scope(db, user, template)
    return template


async def _check_template_scope(db: AsyncSession, user: User, template: JourneyTemplate) -> None:
    """`team_id is None` = nội dung dùng chung, chỉ ADMIN sửa được (P0A D10)."""
    if template.team_id is None:
        if user.role != UserRole.ADMIN:
            raise AuthError(403, "FORBIDDEN_ROLE", "auth.forbidden_role")
    else:
        await require_team_scope(template.team_id, user, db)


def _source_dto(source: task_sources.TaskSource) -> TaskSourceResponseDTO:
    return TaskSourceResponseDTO(
        document_title=source.document_title,
        version_label=source.version_label,
        version_id=source.version_id,
        document_url=source.document_url,
        section_heading=source.section_heading,
        quote=source.quote,
    )


def _employee_task_dto(
    details: journey_service.TaskDetail,
    prerequisites: dict[int, list[tuple[str, bool]]],
    sources: dict[int, list[task_sources.TaskSource]],
) -> EmployeeTaskResponseDTO:
    return EmployeeTaskResponseDTO(
        id=details.task.id,
        task_template_id=details.template.id,
        title=details.template.title,
        body_markdown=details.template.body_markdown,
        required=details.template.required,
        stage_id=details.stage.id,
        stage_title=details.stage.title,
        stage_sort_order=details.stage.sort_order,
        sort_order=details.template.sort_order,
        task_group=details.template.task_group,
        status=details.task.status,
        completed_at=details.task.completed_at,
        prerequisites=[
            EmployeePrerequisiteResponseDTO(title=title, done=done)
            for title, done in prerequisites.get(details.task.id, [])
        ],
        sources=[_source_dto(source) for source in sources.get(details.template.id, [])],
    )


@router.get("/me/journey", response_model=EmployeeJourneyResponseDTO)
async def get_my_journey(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeJourneyResponseDTO:
    """Lộ trình đang hoạt động của chính người gọi — tự tạo lần đầu từ template PUBLISHED (P2.md)."""
    journey = await journey_service.get_or_start_journey(db, user)
    template = await db.get(JourneyTemplate, journey.journey_template_id)
    details = await journey_service.list_task_details(db, journey.id)
    prerequisites = await journey_service.list_prerequisites(db, journey.id)
    sources = await task_sources.sources_by_task(db, [d.template.id for d in details])
    return EmployeeJourneyResponseDTO(
        id=journey.id,
        journey_template_id=journey.journey_template_id,
        journey_title=template.title if template else "",
        started_at=journey.started_at,
        tasks=[_employee_task_dto(d, prerequisites, sources) for d in details],
    )


@router.post("/me/tasks/{employee_task_id}/opened", status_code=204)
async def mark_my_task_opened(
    employee_task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """Ghi "việc vừa mở" để Viga hiểu "việc này" mà giao diện không cần gửi `task_id` (mục 15.3e). Không đổi trạng thái việc."""
    await snapshot_service.mark_task_opened(db, user, employee_task_id)
    return Response(status_code=204)


@router.post("/me/tasks/{employee_task_id}/complete", response_model=EmployeeTaskResponseDTO)
async def complete_my_task(
    employee_task_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeTaskResponseDTO:
    """Nhân viên tự bấm "Hoàn thành" — 1 hành động duy nhất cho cả task (P0A D1), idempotent nếu đã DONE."""
    task = await journey_service.complete_task(db, user, employee_task_id)
    details = await journey_service.list_task_details(db, task.employee_journey_id)
    prerequisites = await journey_service.list_prerequisites(db, task.employee_journey_id)
    current = next(d for d in details if d.task.id == task.id)
    sources = await task_sources.sources_by_task(db, [current.template.id])
    return _employee_task_dto(current, prerequisites, sources)


def _profile_dto(profile: profile_service.Profile) -> EmployeeProfileResponseDTO:
    return EmployeeProfileResponseDTO(
        id=profile.user.id,
        email=profile.user.email,
        display_name=profile.user.display_name,
        role=profile.user.role,
        department=profile.department,
        joined_at=profile.user.created_at,
        last_login_at=profile.user.last_login_at,
        journey_started_at=profile.journey_started_at,
        tasks_total=profile.tasks_total,
        tasks_done=profile.tasks_done,
        required_total=profile.required_total,
        required_done=profile.required_done,
    )


@router.get("/me/profile", response_model=EmployeeProfileResponseDTO)
async def get_my_profile(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeProfileResponseDTO:
    return _profile_dto(await profile_service.get_profile(db, user))


@router.patch("/me/profile", response_model=EmployeeProfileResponseDTO)
async def update_my_profile(
    body: UpdateMyProfileRequestDTO,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> EmployeeProfileResponseDTO:
    await profile_service.update_display_name(db, user, body.display_name)
    return _profile_dto(await profile_service.get_profile(db, user))


@router.post("/me/password", status_code=204)
async def change_my_password(
    body: ChangeMyPasswordRequestDTO,
    response: Response,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """Đổi mật khẩu: mọi phiên cũ bị thu hồi, riêng thiết bị đang dùng nhận cookie mới để không bị đăng xuất."""
    await profile_service.change_password(db, user, body.current_password, body.new_password)
    token, _ = start_session(user, session_secret(settings), settings.session_ttl_seconds)
    set_session_cookie(response, token, settings)


@router.get("/me/documents", response_model=list[EmployeeDocumentResponseDTO])
async def list_my_documents(
    _user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EmployeeDocumentResponseDTO]:
    """Thư viện tài liệu cho nhân viên: chỉ tài liệu đang hiệu lực; xem nội dung qua `/chat/documents/{version_id}`."""
    return [EmployeeDocumentResponseDTO(**vars(item)) for item in await profile_service.list_employee_documents(db)]


@router.get("/dashboard", response_model=HrDashboardResponseDTO)
async def get_hr_dashboard(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> HrDashboardResponseDTO:
    """KPI thật cho Tổng quan HR — theo phạm vi team của người gọi (ADMIN xem phần dùng chung, team_id=None)."""
    team_id = await template_service.hr_team_id(db, user) if user.role == UserRole.HR else None
    dashboard = await template_service.get_hr_dashboard(db, team_id=team_id)
    return HrDashboardResponseDTO(
        journey_template_count=dashboard.journey_template_count,
        journey_stage_count=dashboard.journey_stage_count,
        task_template_count=dashboard.task_template_count,
        document_count=dashboard.document_count,
    )


@router.get("/documents")
async def list_documents(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentListItemResponseDTO]:
    items = await template_service.list_documents(db)
    return [_document_item(item) for item in items]


@router.get("/stages")
async def list_stage_options(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[StageOptionResponseDTO]:
    """Giai đoạn (bản nháp) có sẵn trong phạm vi HR — cho màn "Tạo task bằng AI" chọn đích có sẵn."""
    team_id = await template_service.hr_team_id(db, user) if user.role == UserRole.HR else None
    options = await template_service.list_stage_options(db, team_id=team_id)
    return [
        StageOptionResponseDTO(
            id=o.id, journey_template_id=o.journey_template_id, title=o.title, template_title=o.template_title
        )
        for o in options
    ]


@router.post("/journey-templates", response_model=JourneyTemplateResponseDTO)
async def create_journey_template(
    body: CreateJourneyTemplateRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JourneyTemplateResponseDTO:
    template = await template_service.create_journey_template(
        db, user=user, code=body.code, title=body.title, description=body.description
    )
    return JourneyTemplateResponseDTO.model_validate(template, from_attributes=True)


@router.post("/journey-templates/{template_id}/stages", response_model=JourneyStageResponseDTO)
async def create_journey_stage(
    template_id: int,
    body: CreateJourneyStageRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JourneyStageResponseDTO:
    template = await _require_template_scope(db, user, template_id)
    stage = await template_service.add_stage(db, template=template, title=body.title, sort_order=body.sort_order)
    return JourneyStageResponseDTO.model_validate(stage, from_attributes=True)


@router.get("/documents/{document_version_id}/original")
async def get_original_document(
    document_version_id: int,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    """Tải/mở file gốc — KHÔNG nhảy tới đúng đoạn (chỉ bản Markdown ở `/chat/documents/{id}` làm được
    việc đó). `cloudinary`: chuyển hướng tới `secure_url`; `local` (dev): trả thẳng file trên đĩa."""
    location = await resolve_original_document(db, document_version_id=document_version_id, settings=settings)
    if location.kind == "url":
        return RedirectResponse(location.value, status_code=307)
    return FileResponse(location.value, media_type=location.mime_type, filename=location.filename)


@router.post("/ai/task-proposals")
async def propose_ai_tasks(
    body: CreateAiTaskProposalRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
    llm: Annotated[ChatCompletionPort, Depends(get_chat_completion_port)],
) -> list[AiTaskProposalResponseDTO]:
    return await ai_task_service.propose_tasks(db, document_version_id=body.document_version_id, llm=llm)


@router.post("/stages/{stage_id}/tasks/from-proposal", response_model=TaskTemplateResponseDTO)
async def accept_ai_task_proposal(
    stage_id: int,
    body: AcceptAiTaskProposalRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskTemplateResponseDTO:
    stage: JourneyStage
    template: JourneyTemplate
    stage, template = await ai_task_service.load_stage_and_template(db, stage_id)
    await _check_template_scope(db, user, template)
    task = await ai_task_service.create_task_from_proposal(db, stage=stage, template=template, payload=body)
    return TaskTemplateResponseDTO.model_validate(task, from_attributes=True)


@router.patch("/documents/{document_id}/status", response_model=DocumentListItemResponseDTO)
async def set_document_status(
    document_id: int,
    body: SetDocumentStatusRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentListItemResponseDTO:
    """Ẩn/kích hoạt lại tài liệu — không xóa cứng (giữ lịch sử ingest và task đang trích dẫn)."""
    await template_service.set_document_status(db, document_id=document_id, status=DocumentStatus(body.status))
    items = [item for item in await template_service.list_documents(db) if item.id == document_id]
    if not items:
        raise PortalError(404, "DOCUMENT_NOT_FOUND", "portal.document_not_found")
    item = items[0]
    return _document_item(item)


@router.get("/journey-templates/mine")
async def list_my_templates(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[TemplateNodeResponseDTO]:
    """Cây lộ trình đầy đủ trong phạm vi HR — nguồn dữ liệu thật cho "Quản lý task"."""
    team_id = await template_service.hr_team_id(db, user) if user.role == UserRole.HR else None
    nodes = await template_service.list_my_templates(db, team_id=team_id)
    sources = await task_sources.sources_by_task(db, [t.id for n in nodes for s in n.stages for t in s.tasks])
    return [
        TemplateNodeResponseDTO(
            id=n.id,
            code=n.code,
            title=n.title,
            status=n.status,
            team_id=n.team_id,
            stages=[
                StageNodeResponseDTO(
                    id=s.id,
                    title=s.title,
                    sort_order=s.sort_order,
                    tasks=[
                        TaskNodeResponseDTO(
                            id=t.id,
                            journey_stage_id=t.journey_stage_id,
                            title=t.title,
                            body_markdown=t.body_markdown,
                            required=t.required,
                            sort_order=t.sort_order,
                            team_id=t.team_id,
                            depends_on=t.depends_on,
                            task_group=t.task_group,
                            sources=[_source_dto(source) for source in sources.get(t.id, [])],
                        )
                        for t in s.tasks
                    ],
                )
                for s in n.stages
            ],
        )
        for n in nodes
    ]


@router.post("/stages/{stage_id}/tasks", response_model=TaskTemplateResponseDTO)
async def create_task_manual(
    stage_id: int,
    body: CreateTaskManualRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskTemplateResponseDTO:
    stage, template = await ai_task_service.load_stage_and_template(db, stage_id)
    await _check_template_scope(db, user, template)
    task = await template_service.create_task_manual(
        db,
        stage=stage,
        title=body.title,
        body_markdown=body.body_markdown,
        required=body.required,
        sort_order=body.sort_order,
        depends_on=body.depends_on,
        task_group=body.task_group,
    )
    return TaskTemplateResponseDTO.model_validate(task, from_attributes=True)


async def _require_task_scope(db: AsyncSession, user: User, task_id: int) -> TaskTemplate:
    task = await template_service.get_task_template(db, task_id)
    stage = await db.get(JourneyStage, task.journey_stage_id)
    assert stage is not None
    _, template = await ai_task_service.load_stage_and_template(db, stage.id)
    await _check_template_scope(db, user, template)
    return task


@router.patch("/task-templates/{task_id}", response_model=TaskTemplateResponseDTO)
async def update_task_template(
    task_id: int,
    body: UpdateTaskTemplateRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> TaskTemplateResponseDTO:
    task = await _require_task_scope(db, user, task_id)
    task = await template_service.update_task_template(
        db,
        task=task,
        title=body.title,
        body_markdown=body.body_markdown,
        required=body.required,
        journey_stage_id=body.journey_stage_id,
        sort_order=body.sort_order,
        depends_on=body.depends_on,
        task_group=body.task_group,
    )
    return TaskTemplateResponseDTO.model_validate(task, from_attributes=True)


@router.delete("/task-templates/{task_id}", status_code=204)
async def delete_task_template(
    task_id: int,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    task = await _require_task_scope(db, user, task_id)
    await template_service.delete_task_template(db, task=task)


@router.get("/employees")
async def list_employees(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[EmployeeSummaryResponseDTO]:
    """Danh sách nhân viên trong team của HR kèm tiến độ lộ trình — dùng lại bảng đã có."""
    team_id = await template_service.hr_team_id(db, user) if user.role == UserRole.HR else None
    summaries = await employee_service.list_employees(db, team_id=team_id)
    return [
        EmployeeSummaryResponseDTO(
            id=s.id,
            display_name=s.display_name,
            email=s.email,
            department=s.department,
            journey_started=s.journey_started,
            tasks_done=s.tasks_done,
            tasks_total=s.tasks_total,
            current_task_title=s.current_task_title,
            current_stage_title=s.current_stage_title,
            current_status=s.current_status,
        )
        for s in summaries
    ]


def _document_item(item: template_service.DocumentListItem) -> DocumentListItemResponseDTO:
    return DocumentListItemResponseDTO(**vars(item))


@router.get("/document-categories")
async def list_document_categories(
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentCategoryResponseDTO]:
    categories = await template_service.list_document_categories(db)
    return [DocumentCategoryResponseDTO(slug=c.slug, name=c.name) for c in categories]


@router.patch("/documents/{document_id}", response_model=DocumentListItemResponseDTO)
async def update_document(
    document_id: int,
    body: UpdateDocumentRequestDTO,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentListItemResponseDTO:
    await template_service.update_document(
        db, document_id=document_id, title=body.title, category_slug=body.category_slug
    )
    items = [item for item in await template_service.list_documents(db) if item.id == document_id]
    return _document_item(items[0])


@router.post("/journey-templates/{template_id}/publish", response_model=JourneyTemplateResponseDTO)
async def publish_journey_template(
    template_id: int,
    user: Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> JourneyTemplateResponseDTO:
    template = await _require_template_scope(db, user, template_id)
    template = await template_service.publish_template(db, template=template)
    return JourneyTemplateResponseDTO.model_validate(template, from_attributes=True)
