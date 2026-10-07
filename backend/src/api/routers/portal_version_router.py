"""`/api/v1/portal`: phiên bản của từng ngày (HR) và thông báo thay đổi lộ trình (nhân viên).

Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md (mục 6).
- HR (đúng team, hoặc ADMIN với nội dung dùng chung): tạo bản nháp, áp dụng (có xem trước), xóa nháp, theo dõi triển khai.
- Nhân viên: xem thông báo thay đổi, xem hậu quả của nút "Cập nhật", cập nhật hoặc giữ bản cũ.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, get_db, require_role
from src.api.routers.portal_router import _check_template_scope
from src.dto.request.portal_request_dto import (
    CreateStageVersionRequestDTO,
    CreateTaskManualRequestDTO,
    UpdateStageVersionRequestDTO,
)
from src.dto.response.portal_response_dto import (
    AcceptChangeResponseDTO,
    ApplyPreviewResponseDTO,
    ApplyResultResponseDTO,
    ChangePreviewResponseDTO,
    JourneyNoticeResponseDTO,
    RolloutRowResponseDTO,
    StageVersionResponseDTO,
    TaskChangeResponseDTO,
    TaskTemplateResponseDTO,
)
from src.model.enums import UserRole
from src.model.stage_version import StageVersion
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.portal import rollout_service, stage_version_service, template_service

router = APIRouter(prefix="/api/v1/portal", tags=["portal-versions"])

StaffUser = Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))]
CurrentUser = Annotated[User, Depends(get_current_user)]
Db = Annotated[AsyncSession, Depends(get_db)]


async def _version_dto(db: AsyncSession, version: StageVersion) -> StageVersionResponseDTO:
    count = await db.scalar(select(func.count(TaskTemplate.id)).where(TaskTemplate.stage_version_id == version.id))
    return StageVersionResponseDTO(
        id=version.id,
        journey_stage_id=version.journey_stage_id,
        version_no=version.version_no,
        status=version.status,
        note=version.note,
        based_on_version_id=version.based_on_version_id,
        applied_at=version.applied_at,
        created_at=version.created_at,
        task_count=int(count or 0),
    )


async def _staff_version(db: AsyncSession, user: User, version_id: int) -> StageVersion:
    """Phiên bản trong phạm vi của người gọi (HR đúng team; nội dung dùng chung chỉ ADMIN)."""
    version = await stage_version_service.get_version(db, version_id)
    await _check_template_scope(db, user, await stage_version_service.get_template_of(db, version))
    return version


# ───────────────────────────── HR: phiên bản của một ngày ─────────────────────────────


@router.post("/stages/{stage_id}/versions", response_model=StageVersionResponseDTO, status_code=201)
async def create_stage_version(
    stage_id: int, body: CreateStageVersionRequestDTO, user: StaffUser, db: Db
) -> StageVersionResponseDTO:
    """Tạo bản nháp mới của một ngày (sao chép từ bản chỉ định, mặc định bản đang áp dụng)."""
    stage = await stage_version_service.get_stage(db, stage_id)
    template = await template_service.get_journey_template(db, stage.journey_template_id)
    await _check_template_scope(db, user, template)
    version = await stage_version_service.create_draft(
        db, stage=stage, from_version_id=body.from_version_id, note=body.note, user=user
    )
    return await _version_dto(db, version)


@router.patch("/stage-versions/{version_id}", response_model=StageVersionResponseDTO)
async def update_stage_version(
    version_id: int, body: UpdateStageVersionRequestDTO, user: StaffUser, db: Db
) -> StageVersionResponseDTO:
    version = await _staff_version(db, user, version_id)
    return await _version_dto(db, await stage_version_service.update_note(db, version, body.note))


@router.delete("/stage-versions/{version_id}", status_code=204)
async def delete_stage_version(version_id: int, user: StaffUser, db: Db) -> Response:
    version = await _staff_version(db, user, version_id)
    await stage_version_service.delete_draft(db, version)
    return Response(status_code=204)


@router.post("/stage-versions/{version_id}/tasks", response_model=TaskTemplateResponseDTO)
async def create_task_in_version(
    version_id: int, body: CreateTaskManualRequestDTO, user: StaffUser, db: Db
) -> TaskTemplateResponseDTO:
    version = await _staff_version(db, user, version_id)
    stage = await stage_version_service.get_stage(db, version.journey_stage_id)
    task = await template_service.create_task_manual(
        db,
        stage=stage,
        user=user,
        version=version,
        title=body.title,
        body_markdown=body.body_markdown,
        required=body.required,
        sort_order=body.sort_order,
        depends_on=body.depends_on,
        task_group=body.task_group,
    )
    return TaskTemplateResponseDTO.model_validate(task, from_attributes=True)


@router.get("/stage-versions/{version_id}/apply-preview", response_model=ApplyPreviewResponseDTO)
async def preview_apply_stage_version(version_id: int, user: StaffUser, db: Db) -> ApplyPreviewResponseDTO:
    """Xem trước khi áp dụng, KHÔNG ghi gì: số việc đổi, thêm, bỏ và số nhân viên sẽ nhận thông báo."""
    version = await _staff_version(db, user, version_id)
    preview = await rollout_service.preview_apply(db, version)
    return ApplyPreviewResponseDTO(
        modified=preview.modified,
        added=preview.added,
        removed=preview.removed,
        employee_count=preview.employee_count,
        has_applied_before=preview.has_applied_before,
    )


@router.post("/stage-versions/{version_id}/apply", response_model=ApplyResultResponseDTO)
async def apply_stage_version(version_id: int, user: StaffUser, db: Db) -> ApplyResultResponseDTO:
    """Áp dụng bản nháp: bản đang áp dụng thành lưu trữ. Lộ trình nhân viên đã có KHÔNG đổi; họ nhận thông báo."""
    version = await _staff_version(db, user, version_id)
    result = await stage_version_service.apply_version(db, version=version, user=user)
    return ApplyResultResponseDTO(version=await _version_dto(db, result.version), notified_count=result.notified_count)


@router.get("/stage-versions/{version_id}/rollout", response_model=list[RolloutRowResponseDTO])
async def get_stage_version_rollout(version_id: int, user: StaffUser, db: Db) -> list[RolloutRowResponseDTO]:
    """Theo dõi triển khai: nhân viên nào chưa xem, đã xem, đã cập nhật, giữ bản cũ."""
    version = await _staff_version(db, user, version_id)
    rows = await rollout_service.rollout_for_version(db, version)
    return [
        RolloutRowResponseDTO(
            notice_id=r.notice_id,
            user_id=r.user_id,
            display_name=r.display_name,
            email=r.email,
            state=r.state,
            pending=r.pending,
            accepted=r.accepted,
            dismissed=r.dismissed,
            total=r.total,
            read_at=r.read_at,
        )
        for r in rows
    ]


# ───────────────────────────── Nhân viên: thông báo thay đổi ─────────────────────────────


def _change_dto(change: rollout_service.ChangeDetail) -> TaskChangeResponseDTO:
    return TaskChangeResponseDTO(
        id=change.id,
        notice_id=change.notice_id,
        kind=change.kind,
        status=change.status,
        task_title=change.task_title,
        employee_task_id=change.employee_task_id,
        employee_status=change.employee_status,
        stage_title=change.stage_title,
        before=change.before,
        after=change.after,
        changed_fields=change.changed_fields,
        informational=change.informational,
    )


@router.get("/me/journey/notices", response_model=list[JourneyNoticeResponseDTO])
async def list_my_notices(user: CurrentUser, db: Db) -> list[JourneyNoticeResponseDTO]:
    notices = await rollout_service.list_notices(db, user)
    return [
        JourneyNoticeResponseDTO(
            id=n.id,
            journey_stage_id=n.journey_stage_id,
            stage_title=n.stage_title,
            version_no=n.version_no,
            created_at=n.created_at,
            read_at=n.read_at,
            new_stage=n.new_stage,
            changes=[_change_dto(c) for c in n.changes],
        )
        for n in notices
    ]


@router.post("/me/journey/notices/{notice_id}/read", status_code=204)
async def mark_my_notice_read(notice_id: int, user: CurrentUser, db: Db) -> Response:
    await rollout_service.mark_read(db, user, notice_id)
    return Response(status_code=204)


@router.post("/me/journey/notices/{notice_id}/accept-all", response_model=AcceptChangeResponseDTO)
async def accept_all_my_changes(notice_id: int, user: CurrentUser, db: Db) -> AcceptChangeResponseDTO:
    return AcceptChangeResponseDTO(updated_change_ids=await rollout_service.accept_all(db, user, notice_id))


@router.get("/me/journey/changes/{change_id}/preview", response_model=ChangePreviewResponseDTO)
async def preview_my_change(change_id: int, user: CurrentUser, db: Db) -> ChangePreviewResponseDTO:
    """Hộp ghi chú trước khi bấm "Cập nhật": điều gì sẽ xảy ra với việc này. KHÔNG ghi gì."""
    preview = await rollout_service.preview_change(db, user, change_id)
    return ChangePreviewResponseDTO(
        change_id=preview.change_id,
        kind=preview.kind,
        keeps_done=preview.keeps_done,
        removes_task=preview.removes_task,
        also_update=preview.also_update,
        locked_until=preview.locked_until,
    )


@router.post("/me/journey/changes/{change_id}/accept", response_model=AcceptChangeResponseDTO)
async def accept_my_change(change_id: int, user: CurrentUser, db: Db) -> AcceptChangeResponseDTO:
    """Nhân viên bấm "Cập nhật": thay bằng nội dung mới nhất (kèm các việc liên quan), giữ nguyên trạng thái."""
    return AcceptChangeResponseDTO(updated_change_ids=await rollout_service.accept_change(db, user, change_id))


@router.post("/me/journey/changes/{change_id}/dismiss", status_code=204)
async def dismiss_my_change(change_id: int, user: CurrentUser, db: Db) -> Response:
    await rollout_service.dismiss_change(db, user, change_id)
    return Response(status_code=204)
