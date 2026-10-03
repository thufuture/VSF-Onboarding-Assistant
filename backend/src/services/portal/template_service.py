"""HR tạo JourneyTemplate/JourneyStage thủ công — tối thiểu để có chỗ nhận task từ AI (P4B mục 8).

CRUD đầy đủ (task thủ công, dependency, publish) để lại cho lượt sau; ở đây chỉ đủ để test
luồng upload + AI đề xuất + accept end-to-end.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import cast

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import DocumentStatus, JourneyTemplateStatus, VersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.task_dependency import TaskDependency
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.ingest.ingest_service import today_in
from src.services.ingest.version_lifecycle import get_current_version
from src.services.portal.errors import PortalError


async def hr_team_id(session: AsyncSession, user: User) -> int | None:
    """Team đầu tiên (theo id) mà HR thuộc — Portal coi mỗi user chỉ ở 1 team (P1/P1.md mục 0)."""
    return cast(
        "int | None",
        await session.scalar(
            select(TeamMember.team_id).where(TeamMember.user_id == user.id).order_by(TeamMember.team_id).limit(1)
        ),
    )


async def create_journey_template(
    session: AsyncSession, *, user: User, code: str, title: str, description: str | None
) -> JourneyTemplate:
    team_id = await hr_team_id(session, user)
    template = JourneyTemplate(
        code=code,
        title=title,
        description=description,
        status=JourneyTemplateStatus.DRAFT.value,
        team_id=team_id,
        created_by=user.id,
    )
    session.add(template)
    await session.commit()
    return template


async def get_journey_template(session: AsyncSession, journey_template_id: int) -> JourneyTemplate:
    """Dùng ở router để kiểm quyền (team scope) trước khi gọi hàm ghi DB bên dưới."""
    template = await session.get(JourneyTemplate, journey_template_id)
    if template is None:
        raise PortalError(404, "JOURNEY_TEMPLATE_NOT_FOUND", "portal.journey_template_not_found")
    return template


async def add_stage(session: AsyncSession, *, template: JourneyTemplate, title: str, sort_order: int) -> JourneyStage:
    if template.status != JourneyTemplateStatus.DRAFT:
        raise PortalError(409, "TEMPLATE_ALREADY_PUBLISHED", "portal.template_already_published")
    stage = JourneyStage(journey_template_id=template.id, title=title, sort_order=sort_order)
    session.add(stage)
    await session.commit()
    return stage


@dataclass
class StageOption:
    id: int
    journey_template_id: int
    title: str
    template_title: str


async def list_stage_options(session: AsyncSession, *, team_id: int | None) -> list[StageOption]:
    """Giai đoạn có sẵn trong phạm vi HR — cho màn "Tạo task bằng AI" chọn đích thay vì luôn tạo mới."""
    template_scope = (JourneyTemplate.team_id == team_id) if team_id is not None else JourneyTemplate.team_id.is_(None)
    rows = (
        await session.execute(
            select(JourneyStage, JourneyTemplate.title)
            .join(JourneyTemplate, JourneyTemplate.id == JourneyStage.journey_template_id)
            .where(template_scope, JourneyTemplate.status == JourneyTemplateStatus.DRAFT)
            .order_by(JourneyStage.journey_template_id, JourneyStage.sort_order)
        )
    ).all()
    return [
        StageOption(
            id=stage.id, journey_template_id=stage.journey_template_id, title=stage.title, template_title=template_title
        )
        for stage, template_title in rows
    ]


@dataclass
class HrDashboard:
    journey_template_count: int
    journey_stage_count: int
    task_template_count: int
    document_count: int


async def get_hr_dashboard(session: AsyncSession, *, team_id: int | None) -> HrDashboard:
    """KPI thật cho Tổng quan: lộ trình/giai đoạn/task theo phạm vi team của HR; tài liệu không có team (INV9)."""
    template_scope = (JourneyTemplate.team_id == team_id) if team_id is not None else JourneyTemplate.team_id.is_(None)
    template_count = await session.scalar(select(func.count(JourneyTemplate.id)).where(template_scope)) or 0
    stage_count = (
        await session.scalar(
            select(func.count(JourneyStage.id))
            .join(JourneyTemplate, JourneyTemplate.id == JourneyStage.journey_template_id)
            .where(template_scope)
        )
        or 0
    )
    task_scope = (TaskTemplate.team_id == team_id) if team_id is not None else TaskTemplate.team_id.is_(None)
    task_count = await session.scalar(select(func.count(TaskTemplate.id)).where(task_scope)) or 0
    document_count = await session.scalar(select(func.count(Document.id))) or 0
    return HrDashboard(
        journey_template_count=template_count,
        journey_stage_count=stage_count,
        task_template_count=task_count,
        document_count=document_count,
    )


@dataclass
class DocumentListItem:
    id: int
    title: str
    category_name: str
    status: str
    updated_at: datetime
    latest_version_id: int | None
    section_count: int
    source_key: str | None
    category_slug: str
    owner_name: str | None
    task_titles: list[str]
    current_version_label: str | None = None
    version_count: int = 0
    draft_count: int = 0
    processing_count: int = 0
    processing_version_ids: list[int] = field(default_factory=list)


async def list_documents(session: AsyncSession, today: date | None = None) -> list[DocumentListItem]:
    """Danh sách tài liệu thật cho trang "Tài liệu" — không lọc theo team (INV9: không có ACL tài liệu)."""
    today = today or today_in()
    rows = (
        await session.execute(
            select(Document, DocumentCategory.name, DocumentCategory.slug, User.display_name)
            .join(DocumentCategory, DocumentCategory.id == Document.category_id)
            .outerjoin(User, User.id == Document.owner_id)
            .order_by(Document.updated_at.desc())
        )
    ).all()
    items: list[DocumentListItem] = []
    for document, category_name, category_slug, owner_name in rows:
        task_titles = list(
            (
                await session.scalars(
                    select(TaskTemplate.title)
                    .join(TaskSourceMapping, TaskSourceMapping.task_template_id == TaskTemplate.id)
                    .where(TaskSourceMapping.document_id == document.id)
                    .distinct()
                    .order_by(TaskTemplate.title)
                )
            ).all()
        )
        latest_version = await get_current_version(session, document.id, today)
        version_count = (
            await session.scalar(
                select(func.count(DocumentVersion.id)).where(DocumentVersion.document_id == document.id)
            )
            or 0
        )
        draft_count = (
            await session.scalar(
                select(func.count(DocumentVersion.id)).where(
                    DocumentVersion.document_id == document.id, DocumentVersion.status == VersionStatus.DRAFT
                )
            )
            or 0
        )
        processing_version_ids = list(
            (
                await session.scalars(
                    select(DocumentVersion.id).where(
                        DocumentVersion.document_id == document.id, DocumentVersion.status == VersionStatus.PROCESSING
                    )
                )
            ).all()
        )
        section_count = 0
        if latest_version is not None:
            section_count = (
                await session.scalar(
                    select(func.count(DocumentSection.id)).where(DocumentSection.version_id == latest_version.id)
                )
                or 0
            )
        items.append(
            DocumentListItem(
                id=document.id,
                title=document.title,
                category_name=category_name,
                status=document.status,
                updated_at=document.updated_at,
                latest_version_id=latest_version.id if latest_version else None,
                section_count=section_count,
                source_key=document.source_key,
                category_slug=category_slug,
                owner_name=owner_name,
                task_titles=task_titles,
                current_version_label=latest_version.version_label if latest_version else None,
                version_count=version_count,
                draft_count=draft_count,
                processing_count=len(processing_version_ids),
                processing_version_ids=processing_version_ids,
            )
        )
    return items


async def list_document_categories(session: AsyncSession) -> list[DocumentCategory]:
    rows = await session.scalars(
        select(DocumentCategory).where(DocumentCategory.is_active.is_(True)).order_by(DocumentCategory.sort_order)
    )
    return list(rows.all())


async def update_document(session: AsyncSession, *, document_id: int, title: str, category_slug: str) -> Document:
    document = await session.get(Document, document_id)
    if document is None:
        raise PortalError(404, "DOCUMENT_NOT_FOUND", "portal.document_not_found")
    category = await session.scalar(select(DocumentCategory).where(DocumentCategory.slug == category_slug))
    if category is None:
        raise PortalError(422, "CATEGORY_NOT_FOUND", "portal.category_not_found")
    document.title = title
    document.category_id = category.id
    await session.commit()
    return document


async def set_document_status(session: AsyncSession, *, document_id: int, status: DocumentStatus) -> Document:
    """Chuyển trạng thái tài liệu (ẩn/kích hoạt lại) — không xóa cứng, giữ nguyên lịch sử version."""
    document = await session.get(Document, document_id)
    if document is None:
        raise PortalError(404, "DOCUMENT_NOT_FOUND", "portal.document_not_found")
    document.status = status.value
    await session.commit()
    return document


@dataclass
class TaskNode:
    id: int
    journey_stage_id: int
    title: str
    body_markdown: str
    required: bool
    sort_order: int
    team_id: int | None
    depends_on: list[int]
    task_group: str | None


@dataclass
class StageNode:
    id: int
    title: str
    sort_order: int
    tasks: list[TaskNode]


@dataclass
class TemplateNode:
    id: int
    code: str
    title: str
    status: str
    team_id: int | None
    stages: list[StageNode]


async def list_my_templates(session: AsyncSession, *, team_id: int | None) -> list[TemplateNode]:
    """Cây lộ trình đầy đủ (giai đoạn + task + phụ thuộc) trong phạm vi HR — cho "Quản lý task"."""
    template_scope = (JourneyTemplate.team_id == team_id) if team_id is not None else JourneyTemplate.team_id.is_(None)
    templates = (
        await session.scalars(select(JourneyTemplate).where(template_scope).order_by(JourneyTemplate.id))
    ).all()

    dep_rows = (await session.execute(select(TaskDependency))).all()
    deps_by_task: dict[int, list[int]] = {}
    for (dep,) in dep_rows:
        deps_by_task.setdefault(dep.task_template_id, []).append(dep.depends_on_task_template_id)

    nodes: list[TemplateNode] = []
    for template in templates:
        stages = (
            await session.scalars(
                select(JourneyStage)
                .where(JourneyStage.journey_template_id == template.id)
                .order_by(JourneyStage.sort_order)
            )
        ).all()
        stage_nodes: list[StageNode] = []
        for stage in stages:
            tasks = (
                await session.scalars(
                    select(TaskTemplate)
                    .where(TaskTemplate.journey_stage_id == stage.id)
                    .order_by(TaskTemplate.sort_order)
                )
            ).all()
            stage_nodes.append(
                StageNode(
                    id=stage.id,
                    title=stage.title,
                    sort_order=stage.sort_order,
                    tasks=[
                        TaskNode(
                            id=t.id,
                            journey_stage_id=t.journey_stage_id,
                            title=t.title,
                            body_markdown=t.body_markdown,
                            required=t.required,
                            sort_order=t.sort_order,
                            team_id=t.team_id,
                            depends_on=deps_by_task.get(t.id, []),
                            task_group=t.task_group,
                        )
                        for t in tasks
                    ],
                )
            )
        nodes.append(
            TemplateNode(
                id=template.id,
                code=template.code,
                title=template.title,
                status=template.status,
                team_id=template.team_id,
                stages=stage_nodes,
            )
        )
    return nodes


async def _template_task_ids(session: AsyncSession, template_id: int) -> set[int]:
    rows = await session.scalars(
        select(TaskTemplate.id)
        .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
        .where(JourneyStage.journey_template_id == template_id)
    )
    return set(rows.all())


async def apply_dependencies(
    session: AsyncSession, *, task: TaskTemplate, template_id: int, depends_on: list[int]
) -> None:
    """Tiên quyết chỉ AND (P0A D8): cùng lộ trình, không tự trỏ vào mình, không tạo vòng."""
    wanted = set(depends_on)
    if task.id in wanted:
        raise PortalError(422, "DEPENDENCY_SELF", "portal.dependency_self")
    if not wanted <= await _template_task_ids(session, template_id):
        raise PortalError(422, "DEPENDENCY_OUT_OF_TEMPLATE", "portal.dependency_out_of_template")
    edges = (await session.execute(select(TaskDependency))).all()
    graph: dict[int, set[int]] = {}
    for (edge,) in edges:
        if edge.task_template_id != task.id:
            graph.setdefault(edge.task_template_id, set()).add(edge.depends_on_task_template_id)
    for start_id in wanted:
        seen: set[int] = set()
        stack = [start_id]
        while stack:
            node = stack.pop()
            if node == task.id:
                raise PortalError(422, "DEPENDENCY_CYCLE", "portal.dependency_cycle")
            if node in seen:
                continue
            seen.add(node)
            stack.extend(graph.get(node, ()))
    await session.execute(delete(TaskDependency).where(TaskDependency.task_template_id == task.id))
    for dep_id in wanted:
        session.add(TaskDependency(task_template_id=task.id, depends_on_task_template_id=dep_id))


async def place_in_stage(session: AsyncSession, *, task: TaskTemplate, stage_id: int, position: int | None) -> None:
    """Đặt task vào vị trí `position` (1-based) của giai đoạn rồi đánh số lại 1..n; None = cuối."""
    others = list(
        (
            await session.scalars(
                select(TaskTemplate)
                .where(TaskTemplate.journey_stage_id == stage_id, TaskTemplate.id != task.id)
                .order_by(TaskTemplate.sort_order, TaskTemplate.id)
            )
        ).all()
    )
    index = len(others) if position is None else max(0, min(position - 1, len(others)))
    others.insert(index, task)
    task.journey_stage_id = stage_id
    for order, item in enumerate(others, start=1):
        item.sort_order = order


async def create_task_manual(
    session: AsyncSession,
    *,
    stage: JourneyStage,
    title: str,
    body_markdown: str,
    required: bool,
    sort_order: int | None = None,
    depends_on: list[int] | None = None,
    task_group: str | None = None,
) -> TaskTemplate:
    template = await session.get(JourneyTemplate, stage.journey_template_id)
    if template is None or template.status != JourneyTemplateStatus.DRAFT:
        raise PortalError(409, "TEMPLATE_ALREADY_PUBLISHED", "portal.template_already_published")
    task = TaskTemplate(
        journey_stage_id=stage.id,
        title=title,
        body_markdown=body_markdown,
        required=required,
        task_group=task_group,
        sort_order=0,
        team_id=template.team_id,
    )
    session.add(task)
    await session.flush()
    await place_in_stage(session, task=task, stage_id=stage.id, position=sort_order)
    await apply_dependencies(session, task=task, template_id=template.id, depends_on=depends_on or [])
    await session.commit()
    return task


async def get_task_template(session: AsyncSession, task_id: int) -> TaskTemplate:
    task = await session.get(TaskTemplate, task_id)
    if task is None:
        raise PortalError(404, "TASK_TEMPLATE_NOT_FOUND", "portal.task_template_not_found")
    return task


async def update_task_template(
    session: AsyncSession,
    *,
    task: TaskTemplate,
    title: str,
    body_markdown: str,
    required: bool,
    journey_stage_id: int | None = None,
    sort_order: int | None = None,
    depends_on: list[int] | None = None,
    task_group: str | None = None,
) -> TaskTemplate:
    current_stage = await session.get(JourneyStage, task.journey_stage_id)
    assert current_stage is not None
    task.title = title
    task.body_markdown = body_markdown
    task.required = required
    task.task_group = task_group
    target_stage_id = journey_stage_id or task.journey_stage_id
    if target_stage_id != task.journey_stage_id:
        target = await session.get(JourneyStage, target_stage_id)
        if target is None or target.journey_template_id != current_stage.journey_template_id:
            raise PortalError(422, "STAGE_OUT_OF_TEMPLATE", "portal.stage_out_of_template")
    if journey_stage_id is not None or sort_order is not None:
        await place_in_stage(session, task=task, stage_id=target_stage_id, position=sort_order)
    if depends_on is not None:
        await apply_dependencies(
            session, task=task, template_id=current_stage.journey_template_id, depends_on=depends_on
        )
    await session.commit()
    return task


async def publish_template(session: AsyncSession, *, template: JourneyTemplate) -> JourneyTemplate:
    if template.status == JourneyTemplateStatus.PUBLISHED:
        return template
    task_count = await session.scalar(
        select(func.count(TaskTemplate.id))
        .join(JourneyStage, JourneyStage.id == TaskTemplate.journey_stage_id)
        .where(JourneyStage.journey_template_id == template.id)
    )
    if not task_count:
        raise PortalError(409, "TEMPLATE_EMPTY", "portal.template_empty")
    template.status = JourneyTemplateStatus.PUBLISHED.value
    template.published_at = datetime.now(UTC)
    await session.commit()
    return template


async def delete_task_template(session: AsyncSession, *, task: TaskTemplate) -> None:
    """`task_dependencies` có ON DELETE CASCADE trên cả 2 cột nên không cần dọn thủ công."""
    await session.delete(task)
    await session.commit()
