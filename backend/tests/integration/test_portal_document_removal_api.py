# mypy: disable-error-code="no-untyped-def"
"""Tắt hoặc xóa tài liệu khi có task trích dẫn, trên PostgreSQL/ParadeDB thật.

Dữ liệu: hai tài liệu A và B, ba task: T1 chỉ dựa vào A, T2 dựa vào cả A và B, T3 chỉ dựa vào B; một nhân viên đã nhận bản sao của T1.
Quy tắc cần giữ: "xóa task" chỉ xóa task CHỈ dựa vào tài liệu này; task còn nguồn khác được giữ; bản sao của nhân viên không bao giờ
bị xóa; xóa tài liệu mà có task thì bắt buộc chọn giữ hay xóa (không tự quyết).
"""

from collections.abc import AsyncIterator
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from portal_docs_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    app,
    category,
    cleanup_documents,
    client_for,
    login,
    make_member,
    session_factory,
    team,
)
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.employee_journey import EmployeeJourney
from src.model.employee_stage import EmployeeStage
from src.model.employee_task import EmployeeTask
from src.model.enums import Confidentiality, ContentKind, JourneyTemplateStatus, StageVersionStatus, VersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.ingest_service import ingest_document, today_in
from src.services.ingest.storage import LocalStorageAdapter

pytestmark = pytest.mark.integration

API = "/api/v1/portal"


async def _ingest(
    session_factory: async_sessionmaker[AsyncSession],
    tmp_path: Path,
    owner_email: str,
    category: str,
    key: str,
    title: str,
) -> SimpleNamespace:
    path = tmp_path / f"{key}.md"
    path.write_text(
        f"# {title}\n\n" + f"Nội dung của {title} nói về quy trình nhận laptop và tài khoản. " * 8, encoding="utf-8"
    )
    async with session_factory() as session:
        await ingest_document(
            session,
            file_path=path,
            category_slug=category,
            owner_email=owner_email,
            title=title,
            source_key=key,
            version_label="1.0",
            effective_from=today_in(),
            content_kind=ContentKind.GENERAL.value,
            confidentiality=Confidentiality.INTERNAL.value,
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )
        document = await session.scalar(select(Document).where(Document.source_key == key))
        assert document is not None
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id))
        assert version is not None
        section = await session.scalar(select(DocumentSection).where(DocumentSection.version_id == version.id))
        assert section is not None
        return SimpleNamespace(id=document.id, version_id=version.id, section_id=section.id, key=key)


@pytest.fixture
async def world(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    tmp_path: Path,
) -> AsyncIterator[SimpleNamespace]:
    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)
    key_a, key_b = f"rm-a-{uuid4().hex[:8]}", f"rm-b-{uuid4().hex[:8]}"
    cleanup_documents.extend([key_a, key_b])
    a = await _ingest(session_factory, tmp_path, hr.email, category, key_a, "Tài liệu A")
    b = await _ingest(session_factory, tmp_path, hr.email, category, key_b, "Tài liệu B")
    async with session_factory() as session:
        template = JourneyTemplate(
            code=f"rm-{uuid4().hex[:8]}",
            title="Lộ trình thử xóa tài liệu",
            status=JourneyTemplateStatus.PUBLISHED.value,
            team_id=team.id,
            created_by=hr.id,
        )
        session.add(template)
        await session.flush()
        stage = JourneyStage(journey_template_id=template.id, title="Ngày 1", sort_order=1)
        session.add(stage)
        await session.flush()
        version = StageVersion(journey_stage_id=stage.id, version_no=1, status=StageVersionStatus.APPLIED.value)
        session.add(version)
        await session.flush()
        tasks = []
        for order, title in enumerate(("T1 chỉ từ A", "T2 từ A và B", "T3 chỉ từ B")):
            task = TaskTemplate(
                journey_stage_id=stage.id,
                stage_version_id=version.id,
                title=title,
                body_markdown=title,
                sort_order=order,
            )
            session.add(task)
            tasks.append(task)
        await session.flush()
        t1, t2, t3 = tasks

        def cite(task: TaskTemplate, doc: SimpleNamespace) -> TaskSourceMapping:
            return TaskSourceMapping(
                task_template_id=task.id,
                document_id=doc.id,
                document_version_id=doc.version_id,
                document_section_id=doc.section_id,
                quote="Nội dung",
            )

        session.add_all([cite(t1, a), cite(t2, a), cite(t2, b), cite(t3, b)])
        journey = EmployeeJourney(user_id=employee.id, journey_template_id=template.id, team_id=team.id)
        session.add(journey)
        await session.flush()
        emp_stage = EmployeeStage(employee_journey_id=journey.id, journey_stage_id=stage.id, title="Ngày 1")
        session.add(emp_stage)
        await session.flush()
        copy = EmployeeTask(
            employee_journey_id=journey.id,
            employee_stage_id=emp_stage.id,
            source_task_template_id=t1.id,
            origin_key=t1.origin_key,
            title=t1.title,
            body_markdown=t1.body_markdown,
            team_id=team.id,
        )
        session.add(copy)
        await session.commit()
        state = SimpleNamespace(
            hr=hr,
            a=a,
            b=b,
            template_id=template.id,
            t1=t1.id,
            t2=t2.id,
            t3=t3.id,
            journey_id=journey.id,
            copy_id=copy.id,
        )
    yield state
    async with session_factory() as session:
        await session.execute(delete(EmployeeJourney).where(EmployeeJourney.id == state.journey_id))
        await session.execute(delete(TaskTemplate).where(TaskTemplate.journey_stage_id == stage.id))
        await session.execute(delete(JourneyStage).where(JourneyStage.id == stage.id))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.id == state.template_id))
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_([hr.id, employee.id])))
        await session.commit()


async def _task_ids(session_factory: async_sessionmaker[AsyncSession], world: SimpleNamespace) -> set[int]:
    async with session_factory() as session:
        return set(
            (
                await session.scalars(
                    select(TaskTemplate.id).where(TaskTemplate.id.in_([world.t1, world.t2, world.t3]))
                )
            ).all()
        )


async def _count(session_factory: async_sessionmaker[AsyncSession], model: Any, *where: Any) -> int:
    async with session_factory() as session:
        return int(await session.scalar(select(func.count()).select_from(model).where(*where)) or 0)


async def test_impact_separates_tasks_only_from_the_document_and_tasks_with_other_sources(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        body = (await client.get(f"{API}/documents/{world.a.id}/impact")).json()

    assert [t["title"] for t in body["only_tasks"]] == ["T1 chỉ từ A"]
    assert [t["title"] for t in body["shared_tasks"]] == ["T2 từ A và B"]
    assert body["only_tasks"][0]["day_title"] == "Ngày 1" and body["only_tasks"][0]["version_status"] == "APPLIED"
    assert body["employee_copies"] == 1  # nhân viên đã nhận bản sao của T1
    assert body["version_count"] == 1 and body["processing"] is False


async def test_archive_and_keep_tasks_changes_nothing_about_tasks(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.patch(
            f"{API}/documents/{world.a.id}/status", json={"status": "ARCHIVED", "tasks": "KEEP"}
        )

    assert response.status_code == 200 and response.json()["status"] == "ARCHIVED"
    assert await _task_ids(session_factory, world) == {world.t1, world.t2, world.t3}
    assert (
        await _count(session_factory, TaskSourceMapping, TaskSourceMapping.document_id == world.a.id) == 2
    )  # nguồn còn nguyên


async def test_archive_without_a_choice_defaults_to_keeping_tasks(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.patch(f"{API}/documents/{world.a.id}/status", json={"status": "ARCHIVED"})

    assert response.status_code == 200
    assert await _task_ids(session_factory, world) == {world.t1, world.t2, world.t3}


async def test_archive_and_delete_tasks_removes_only_tasks_that_depend_solely_on_the_document(
    app, world, session_factory
):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.patch(
            f"{API}/documents/{world.a.id}/status", json={"status": "ARCHIVED", "tasks": "DELETE"}
        )

    assert response.status_code == 200 and response.json()["status"] == "ARCHIVED"
    assert await _task_ids(session_factory, world) == {world.t2, world.t3}  # T1 mất; T2 còn nguồn B nên được giữ
    # Bản sao của nhân viên vẫn còn, chỉ gỡ liên kết truy nguồn.
    async with session_factory() as session:
        copy = await session.get(EmployeeTask, world.copy_id)
        assert copy is not None and copy.source_task_template_id is None and copy.title == "T1 chỉ từ A"


async def test_reactivating_never_touches_tasks(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        await client.patch(f"{API}/documents/{world.a.id}/status", json={"status": "ARCHIVED", "tasks": "KEEP"})
        response = await client.patch(
            f"{API}/documents/{world.a.id}/status", json={"status": "ACTIVE", "tasks": "DELETE"}
        )

    assert response.status_code == 200 and response.json()["status"] == "ACTIVE"
    assert await _task_ids(session_factory, world) == {world.t1, world.t2, world.t3}


async def test_delete_document_with_tasks_requires_an_explicit_choice(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.delete(f"{API}/documents/{world.a.id}")

    assert response.status_code == 409 and response.json()["code"] == "TASK_CHOICE_REQUIRED"
    assert await _count(session_factory, Document, Document.id == world.a.id) == 1  # chưa xóa gì
    assert await _task_ids(session_factory, world) == {world.t1, world.t2, world.t3}


async def test_delete_document_and_keep_tasks_leaves_tasks_without_the_deleted_source(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.delete(f"{API}/documents/{world.a.id}", params={"tasks": "KEEP"})

    assert response.status_code == 204
    assert await _count(session_factory, Document, Document.id == world.a.id) == 0
    assert await _count(session_factory, DocumentVersion, DocumentVersion.document_id == world.a.id) == 0
    assert await _count(session_factory, DocumentSection, DocumentSection.version_id == world.a.version_id) == 0
    assert await _count(session_factory, DocumentChunk, DocumentChunk.version_id == world.a.version_id) == 0
    assert await _count(session_factory, TaskSourceMapping, TaskSourceMapping.document_id == world.a.id) == 0
    assert await _task_ids(session_factory, world) == {world.t1, world.t2, world.t3}  # task giữ nguyên
    # T2 mất nguồn A nhưng vẫn còn nguồn B; tài liệu B không bị ảnh hưởng.
    assert await _count(session_factory, TaskSourceMapping, TaskSourceMapping.task_template_id == world.t2) == 1
    assert await _count(session_factory, Document, Document.id == world.b.id) == 1
    assert await _count(session_factory, DocumentChunk, DocumentChunk.version_id == world.b.version_id) > 0
    async with session_factory() as session:
        log = await session.scalar(
            select(AuditLog).where(AuditLog.action == "DELETE_DOCUMENT", AuditLog.entity_id == str(world.a.id))
        )
        assert log is not None and log.after == {"tasks": "KEEP", "tasks_deleted": 0, "tasks_kept": 2}


async def test_delete_document_and_delete_tasks_keeps_tasks_that_have_other_sources(app, world, session_factory):
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.delete(f"{API}/documents/{world.a.id}", params={"tasks": "DELETE"})

    assert response.status_code == 204
    assert await _count(session_factory, Document, Document.id == world.a.id) == 0
    assert await _task_ids(session_factory, world) == {world.t2, world.t3}  # chỉ T1 (chỉ từ A) bị xóa
    async with session_factory() as session:
        copy = await session.get(EmployeeTask, world.copy_id)
        assert copy is not None and copy.source_task_template_id is None  # bản sao của nhân viên còn nguyên


async def test_delete_document_without_tasks_needs_no_choice(app, world, session_factory):
    async with session_factory() as session:
        await session.execute(delete(TaskSourceMapping).where(TaskSourceMapping.document_id == world.a.id))
        await session.commit()
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.delete(f"{API}/documents/{world.a.id}")

    assert response.status_code == 204
    assert await _count(session_factory, Document, Document.id == world.a.id) == 0


async def test_cannot_delete_a_document_while_a_version_is_being_processed(app, world, session_factory):
    async with session_factory() as session:
        version = await session.get(DocumentVersion, world.b.version_id)
        assert version is not None
        version.status = VersionStatus.PROCESSING.value
        await session.commit()
    async with client_for(app) as client:
        await login(client, world.hr)
        response = await client.delete(f"{API}/documents/{world.b.id}", params={"tasks": "KEEP"})

    assert response.status_code == 409 and response.json()["code"] == "DOCUMENT_PROCESSING"
    assert await _count(session_factory, Document, Document.id == world.b.id) == 1


async def test_only_hr_or_admin_can_remove_documents_and_unknown_documents_are_404(app, world, make_member, team):
    employee = await make_member("USER", team.id)
    async with client_for(app) as client:
        await login(client, employee)
        assert (await client.get(f"{API}/documents/{world.a.id}/impact")).status_code == 403
        assert (await client.delete(f"{API}/documents/{world.a.id}", params={"tasks": "KEEP"})).status_code == 403
    async with client_for(app) as client:
        await login(client, world.hr)
        assert (await client.get(f"{API}/documents/999999999/impact")).status_code == 404
        assert (await client.delete(f"{API}/documents/999999999")).status_code == 404
