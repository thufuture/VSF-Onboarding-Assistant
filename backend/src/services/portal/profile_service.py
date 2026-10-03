"""Hồ sơ cá nhân của nhân viên: xem, đổi tên hiển thị, đổi mật khẩu; kèm tiến độ lộ trình đang chạy."""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_section import DocumentSection
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import DocumentStatus, EmployeeTaskStatus
from src.model.task_template import TaskTemplate
from src.model.user import User
from src.services.auth.auth_service import department_name, revoke_sessions
from src.services.auth.passwords import hash_password, verify_password
from src.services.ingest.ingest_service import today_in
from src.services.ingest.version_lifecycle import get_current_version
from src.services.portal.errors import PortalError


@dataclass
class Profile:
    user: User
    department: str | None
    journey_started_at: datetime | None
    tasks_total: int
    tasks_done: int
    required_total: int
    required_done: int


async def get_profile(session: AsyncSession, user: User) -> Profile:
    """Không tạo journey (khác `GET /me/journey`): chưa bắt đầu thì mọi số đều 0."""
    journey = await session.scalar(
        select(EmployeeJourney)
        .where(EmployeeJourney.user_id == user.id, EmployeeJourney.deleted_at.is_(None))
        .order_by(EmployeeJourney.id.desc())
        .limit(1)
    )
    total = done = required_total = required_done = 0
    if journey is not None:
        rows = (
            await session.execute(
                select(EmployeeTask.status, TaskTemplate.required)
                .join(TaskTemplate, TaskTemplate.id == EmployeeTask.task_template_id)
                .where(EmployeeTask.employee_journey_id == journey.id)
            )
        ).all()
        for status, required in rows:
            total += 1
            is_done = status == EmployeeTaskStatus.DONE
            done += is_done
            if required:
                required_total += 1
                required_done += is_done
    return Profile(
        user=user,
        department=await department_name(session, user.id),
        journey_started_at=journey.started_at if journey else None,
        tasks_total=total,
        tasks_done=done,
        required_total=required_total,
        required_done=required_done,
    )


async def update_display_name(session: AsyncSession, user: User, display_name: str) -> None:
    name = " ".join(display_name.split())
    if not name:
        raise PortalError(422, "DISPLAY_NAME_EMPTY", "portal.display_name_empty")
    user.display_name = name
    await session.commit()


async def change_password(session: AsyncSession, user: User, current_password: str, new_password: str) -> None:
    """Đổi mật khẩu của chính mình; thu hồi mọi phiên cũ (người gọi tự được cấp cookie mới ở router)."""
    if not verify_password(current_password, user.password_hash):
        raise PortalError(400, "CURRENT_PASSWORD_WRONG", "portal.current_password_wrong")
    if new_password == current_password:
        raise PortalError(400, "PASSWORD_UNCHANGED", "portal.password_unchanged")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    await revoke_sessions(session, user)


@dataclass
class EmployeeDocument:
    id: int
    title: str
    category_name: str
    category_slug: str
    updated_at: datetime
    latest_version_id: int
    section_count: int


async def list_employee_documents(session: AsyncSession, today: date | None = None) -> list[EmployeeDocument]:
    """Tài liệu đang hiệu lực mà Viga cũng dùng làm nguồn (không ACL tài liệu — INV9); bỏ tài liệu đã lưu trữ."""
    today = today or today_in()
    rows = (
        await session.execute(
            select(Document, DocumentCategory.name, DocumentCategory.slug)
            .join(DocumentCategory, DocumentCategory.id == Document.category_id)
            .where(Document.status == DocumentStatus.ACTIVE)
            .order_by(DocumentCategory.sort_order, Document.title)
        )
    ).all()
    items: list[EmployeeDocument] = []
    for document, category_name, category_slug in rows:
        version = await get_current_version(session, document.id, today)
        if version is None:
            continue
        sections = (
            await session.scalar(select(func.count(DocumentSection.id)).where(DocumentSection.version_id == version.id))
            or 0
        )
        items.append(
            EmployeeDocument(
                id=document.id,
                title=document.title,
                category_name=category_name,
                category_slug=category_slug,
                updated_at=document.updated_at,
                latest_version_id=version.id,
                section_count=sections,
            )
        )
    return items
