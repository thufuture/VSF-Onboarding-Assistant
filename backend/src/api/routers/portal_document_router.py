"""`/api/v1/portal` — tài liệu theo phiên bản (bản nháp, sao chép, sửa, kích hoạt) và tiến độ việc nền.

Kế hoạch: plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 14 (chạy nền + phần trăm) và mục 16 (phiên bản).
Chỉ HR và ADMIN. Tải file chỉ tạo **bản nháp**; kích hoạt (cắt chunk, embedding, đóng bản cũ) chạy nền và trả `job_id`.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_storage_port, require_role
from src.config import Settings, get_settings
from src.dto.request.portal_request_dto import (
    ActivateDocumentVersionRequestDTO,
    CopyDocumentVersionRequestDTO,
    CreateAiTaskProposalJobRequestDTO,
    UpdateDocumentVersionRequestDTO,
)
from src.dto.response.portal_response_dto import (
    DiffSegmentResponseDTO,
    DocumentUploadResponseDTO,
    DocumentVersionDetailResponseDTO,
    DocumentVersionResponseDTO,
    JobResponseDTO,
    RecomputeEstimateResponseDTO,
    SectionChangeResponseDTO,
    VersionComparisonResponseDTO,
)
from src.model.enums import UserRole
from src.model.job import Job
from src.model.user import User
from src.services.ingest.ingest_service import today_in
from src.services.ingest.storage import StoragePort
from src.services.portal import ai_task_service, document_diff, document_version_service, job_service
from src.services.portal.errors import PortalError

router = APIRouter(prefix="/api/v1/portal", tags=["portal-documents"])

StaffUser = Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))]
Db = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def _version_dto(item: document_version_service.VersionItem) -> DocumentVersionResponseDTO:
    return DocumentVersionResponseDTO(**vars(item))


def job_dto(job: Job, *, queue_ahead: int | None = None, elapsed_seconds: int | None = None) -> JobResponseDTO:
    return JobResponseDTO(
        id=job.id,
        kind=job.kind,
        status=job.status,
        progress_percent=job.progress_percent,
        stage=job.stage,
        result=job.result,
        error=job.last_error,
        document_version_id=job.document_version_id,
        created_at=job.created_at,
        finished_at=job.finished_at,
        progress=job.progress,
        started_at=job.started_at,
        elapsed_seconds=elapsed_seconds,
        queue_ahead=queue_ahead,
    )


async def _job_with_extras(db: AsyncSession, job: Job) -> JobResponseDTO:
    """Job kèm số việc xếp trước và số giây đã chạy. Số giây do worker tự đo bằng đồng hồ đơn điệu và ghi vào `jobs.progress`
    (không suy ra từ dấu thời gian của DB: đồng hồ máy ảo Docker/WSL của DB dev từng nhảy lệch 101 giây giữa hai lần đọc)."""
    progress = job.progress or {}
    elapsed = progress.get("elapsed_seconds") if isinstance(progress, dict) else None
    return job_dto(
        job,
        queue_ahead=await job_service.queue_ahead(db, job),
        elapsed_seconds=int(elapsed) if isinstance(elapsed, int | float) else None,
    )


@router.post("/documents", response_model=DocumentUploadResponseDTO, status_code=201)
async def upload_document(
    response: Response,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
    storage: Annotated[StoragePort, Depends(get_storage_port)],
    file: Annotated[UploadFile, File()],
    version_label: Annotated[str, Form()],
    title: Annotated[str | None, Form()] = None,
    category_slug: Annotated[str | None, Form()] = None,
    source_key: Annotated[str | None, Form()] = None,
    document_id: Annotated[int | None, Form()] = None,
    effective_from: Annotated[date | None, Form()] = None,
    activate: Annotated[bool, Form()] = False,
) -> DocumentUploadResponseDTO:
    """Tải file thành **bản nháp** (đọc file, lưu file gốc; nhanh, chưa embedding). `activate=true` là "tải và kích
    hoạt luôn": tạo nháp rồi xếp job kích hoạt, trả `job_id` (HTTP 202). Tài liệu mới dùng `title`, `category_slug`,
    `source_key`; tài liệu đã có thì gửi `document_id` (thêm phiên bản mới).
    """
    content = await file.read()
    draft = await document_version_service.create_draft_from_upload(
        db,
        content=content,
        filename=file.filename or "tai-lieu",
        actor=user,
        storage=storage,
        version_label=version_label,
        effective_from=effective_from,
        document_id=document_id,
        title=title,
        category_slug=category_slug,
        source_key=source_key,
        ocr_enabled=settings.ocr_enabled,
    )
    job_id: int | None = draft.job_id
    if activate and not draft.reused and not draft.ocr_pending:
        job = await document_version_service.activate_version(
            db,
            document_id=draft.document_id,
            version_id=draft.version_id,
            actor=user,
            effective_from=effective_from,
            today=today_in(settings.app_timezone),
        )
        job_id = job.id
        response.status_code = 202
    return DocumentUploadResponseDTO(
        document_id=draft.document_id,
        document_version_id=draft.version_id,
        created_document=draft.created_document,
        reused=draft.reused,
        job_id=job_id,
        structure_quality=draft.structure_quality,
        structure_warnings=list(draft.structure_warnings),
    )


@router.get("/documents/{document_id}/versions")
async def list_document_versions(
    document_id: int, _user: StaffUser, db: Db, settings: AppSettings
) -> list[DocumentVersionResponseDTO]:
    items = await document_version_service.list_versions(
        db, document_id=document_id, today=today_in(settings.app_timezone)
    )
    return [_version_dto(item) for item in items]


@router.get("/documents/{document_id}/versions/{version_id}", response_model=DocumentVersionDetailResponseDTO)
async def get_document_version(
    document_id: int, version_id: int, _user: StaffUser, db: Db, settings: AppSettings
) -> DocumentVersionDetailResponseDTO:
    detail = await document_version_service.get_version_detail(
        db, document_id=document_id, version_id=version_id, today=today_in(settings.app_timezone)
    )
    return DocumentVersionDetailResponseDTO(
        version=_version_dto(detail.item),
        document_id=detail.document_id,
        document_title=detail.document_title,
        markdown=detail.markdown,
        can_edit=detail.can_edit,
    )


@router.get("/documents/{document_id}/versions/{version_id}/compare", response_model=VersionComparisonResponseDTO)
async def compare_document_version(
    document_id: int, version_id: int, _user: StaffUser, db: Db, base_version_id: int | None = None
) -> VersionComparisonResponseDTO:
    """ "So với bản trước": mục thêm, xóa, sửa (kèm từng từ đổi) và ước lượng số đoạn phải tính lại embedding. Chỉ đọc."""
    result = await document_diff.compare_with_base(
        db, document_id=document_id, version_id=version_id, base_version_id=base_version_id
    )
    diff = result.diff
    if diff is None:
        return VersionComparisonResponseDTO(
            has_base=False,
            base_version_id=None,
            base_version_label=None,
            base_reason=None,
            added=0,
            removed=0,
            modified=0,
            unchanged=0,
            sections=[],
            recompute=None,
        )
    return VersionComparisonResponseDTO(
        has_base=True,
        base_version_id=result.base_version_id,
        base_version_label=result.base_version_label,
        base_reason=result.base_reason,
        added=diff.added,
        removed=diff.removed,
        modified=diff.modified,
        unchanged=diff.unchanged,
        sections=[
            SectionChangeResponseDTO(
                status=change.status,
                heading=change.heading,
                old_heading=change.old_heading,
                segments=[DiffSegmentResponseDTO(op=s.op, text=s.text) for s in change.segments],
                added_words=change.added_words,
                removed_words=change.removed_words,
            )
            for change in diff.sections
        ],
        recompute=RecomputeEstimateResponseDTO(**vars(diff.recompute)),
    )


@router.post(
    "/documents/{document_id}/versions/{version_id}/copy", response_model=DocumentVersionResponseDTO, status_code=201
)
async def copy_document_version(
    document_id: int,
    version_id: int,
    body: CopyDocumentVersionRequestDTO,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
) -> DocumentVersionResponseDTO:
    """ "Tạo bản mới từ bản này": sao chép thành bản nháp để sửa; bản nguồn không bị đụng tới."""
    draft = await document_version_service.copy_version(
        db, document_id=document_id, version_id=version_id, actor=user, label=body.label
    )
    items = await document_version_service.list_versions(
        db, document_id=document_id, today=today_in(settings.app_timezone)
    )
    return _version_dto(next(item for item in items if item.id == draft.id))


@router.patch("/documents/{document_id}/versions/{version_id}", response_model=DocumentVersionResponseDTO)
async def update_document_version(
    document_id: int,
    version_id: int,
    body: UpdateDocumentVersionRequestDTO,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
) -> DocumentVersionResponseDTO:
    """Sửa bản nháp (nội dung, nhãn, ngày hiệu lực dự kiến); chỉ bản nháp, khóa lạc quan theo `updated_at`."""
    await document_version_service.update_draft(
        db,
        document_id=document_id,
        version_id=version_id,
        actor=user,
        expected_updated_at=body.expected_updated_at,
        markdown=body.markdown,
        label=body.label,
        effective_from=body.effective_from,
        clear_effective_from=body.clear_effective_from,
    )
    items = await document_version_service.list_versions(
        db, document_id=document_id, today=today_in(settings.app_timezone)
    )
    return _version_dto(next(item for item in items if item.id == version_id))


@router.delete("/documents/{document_id}/versions/{version_id}", status_code=204)
async def delete_document_version(document_id: int, version_id: int, user: StaffUser, db: Db) -> Response:
    await document_version_service.delete_draft(db, document_id=document_id, version_id=version_id, actor=user)
    return Response(status_code=204)


@router.post("/documents/{document_id}/versions/{version_id}/activate", response_model=JobResponseDTO, status_code=202)
async def activate_document_version(
    document_id: int,
    version_id: int,
    body: ActivateDocumentVersionRequestDTO,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
) -> JobResponseDTO:
    """Đặt bản này làm bản áp dụng (kể cả bản cũ). Chạy nền; hỏi tiến độ ở `GET /portal/jobs/{job_id}`."""
    job = await document_version_service.activate_version(
        db,
        document_id=document_id,
        version_id=version_id,
        actor=user,
        effective_from=body.effective_from,
        today=today_in(settings.app_timezone),
    )
    return job_dto(job)


@router.post("/ai/task-proposal-jobs", response_model=JobResponseDTO, status_code=202)
async def create_ai_task_proposal_job(
    body: CreateAiTaskProposalJobRequestDTO, user: StaffUser, db: Db
) -> JobResponseDTO:
    """Tạo task bằng AI cho nhiều tài liệu, chạy nền có phần trăm; kết quả đề xuất nằm trong `result` của job."""
    job = await ai_task_service.enqueue_proposal_job(db, user=user, version_ids=body.document_version_ids)
    return await _job_with_extras(db, job)


@router.get("/jobs/{job_id}", response_model=JobResponseDTO)
async def get_job(job_id: int, user: StaffUser, db: Db) -> JobResponseDTO:
    return await _job_with_extras(db, await job_service.get_job_for_user(db, job_id, user))


@router.get("/jobs")
async def list_jobs(user: StaffUser, db: Db, active: bool = False, kind: str | None = None) -> list[JobResponseDTO]:
    jobs = await job_service.list_jobs_for_user(db, user, active_only=active, kind=kind)
    return [await _job_with_extras(db, job) for job in jobs]


__all__ = ["PortalError", "job_dto", "router"]
