"""AI đề xuất task + HR chấp nhận, trên PostgreSQL thật (plan-portal/P4B/P4B.md mục 8.4, 8.5, 8.6).

Dùng `FakeChatCompletion` (không gọi LLM thật) trả JSON cấu hình theo `document_section_id` thật đã
ingest trước đó trong từng test — không hardcode id.
"""

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.dependencies import get_chat_completion_port
from src.config import Settings, get_settings
from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.enums import JourneyTemplateStatus
from src.model.journey_template import JourneyTemplate
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.ingest_service import IngestResult, ingest_document
from src.services.ingest.storage import LocalStorageAdapter

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"
_MD_CONTENT = (
    "# Nhận laptop\n\nNhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR. "
    "Sau khi có laptop và đăng nhập được Outlook và Teams thì mới tiếp tục bước tiếp theo.\n\n"
    "# Đăng ký faceid\n\nĐăng ký faceid chấm công tại tầng 14 theo chỉ dẫn của phòng nhân sự."
)

MakeMember = Callable[[str, int], Awaitable[SimpleNamespace]]


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def team(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SimpleNamespace]:
    async with session_factory() as session:
        row = Team(code=f"team-{uuid4().hex[:8]}", name="Team thử")
        session.add(row)
        await session.commit()
        result = SimpleNamespace(id=row.id)
    yield result
    async with session_factory() as session:
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def category(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[str]:
    slug = f"portal-ai-test-{uuid4().hex[:8]}"
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục thử AI"))
        await session.commit()
    yield slug
    async with session_factory() as session:
        await session.execute(delete(DocumentCategory).where(DocumentCategory.slug == slug))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-ai-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name="Người thử", role=role, password_hash=hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(TeamMember(team_id=team_id, user_id=user.id))
            await session.commit()
            created.append(email)
            return SimpleNamespace(email=email, password=PASSWORD, id=user.id, role=role)

    yield make
    async with session_factory() as session:
        user_ids = (await session.scalars(select(User.id).where(User.email.in_(created)))).all()
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(user_ids)))
        # ingest_document() ghi AuditLog với actor_id = owner — xóa trước khi xóa user (FK RESTRICT).
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        await session.execute(delete(User).where(User.email.in_(created)))
        await session.commit()


async def _ingest_fixture_document(
    session: AsyncSession, category_slug: str, owner_email: str, tmp_path: Path
) -> IngestResult:
    doc_path = tmp_path / "day1-mini.md"
    doc_path.write_text(_MD_CONTENT, encoding="utf-8")
    return await ingest_document(
        session,
        file_path=doc_path,
        category_slug=category_slug,
        owner_email=owner_email,
        title="Tài liệu thử AI",
        source_key=f"ai-src-{uuid4().hex[:10]}",
        version_label="1.0",
        effective_from=date(2024, 1, 1),
        content_kind="GENERAL",
        confidentiality="INTERNAL",
        embedding=FakeEmbeddingAdapter(),
        storage=LocalStorageAdapter(str(tmp_path)),
    )


@pytest.fixture
async def cleanup_documents(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[list[int]]:
    document_ids: list[int] = []
    yield document_ids
    if not document_ids:
        return
    async with session_factory() as session:
        version_ids = list(
            (
                await session.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id.in_(document_ids)))
            ).all()
        )
        if version_ids:
            section_ids = list(
                (
                    await session.scalars(select(DocumentSection.id).where(DocumentSection.version_id.in_(version_ids)))
                ).all()
            )
            if section_ids:
                task_ids = list(
                    (
                        await session.scalars(
                            select(TaskSourceMapping.task_template_id).where(
                                TaskSourceMapping.document_section_id.in_(section_ids)
                            )
                        )
                    ).all()
                )
                await session.execute(
                    delete(TaskSourceMapping).where(TaskSourceMapping.document_section_id.in_(section_ids))
                )
                if task_ids:
                    await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_(task_ids)))
            await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id.in_(version_ids)))
            await session.execute(delete(DocumentSection).where(DocumentSection.version_id.in_(version_ids)))
            await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
        await session.execute(delete(Document).where(Document.id.in_(document_ids)))
        await session.commit()


@pytest.fixture
async def cleanup_templates(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[list[int]]:
    template_ids: list[int] = []
    yield template_ids
    if not template_ids:
        return
    async with session_factory() as session:
        from src.model.journey_stage import JourneyStage

        stage_ids = list(
            (
                await session.scalars(select(JourneyStage.id).where(JourneyStage.journey_template_id.in_(template_ids)))
            ).all()
        )
        if stage_ids:
            await session.execute(delete(TaskTemplate).where(TaskTemplate.journey_stage_id.in_(stage_ids)))
            await session.execute(delete(JourneyStage).where(JourneyStage.id.in_(stage_ids)))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.id.in_(template_ids)))
        await session.commit()


def app_for(session_factory: async_sessionmaker[AsyncSession], llm_response: str) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(3, 900)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_chat_completion_port] = lambda: FakeChatCompletion(llm_response)
    return application


def client_for(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("10.0.0.1", 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def login(client: httpx.AsyncClient, user: SimpleNamespace) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})


async def test_propose_valid_json_returns_proposal_without_completion_mode(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[int],
    tmp_path: Path,
) -> None:
    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        result = await _ingest_fixture_document(session, category, hr.email, tmp_path)
    cleanup_documents.append(result.document_id)

    async with session_factory() as session:
        sections = (
            await session.scalars(select(DocumentSection).where(DocumentSection.version_id == result.version_id))
        ).all()
    first_section = sections[0]

    llm_json = json.dumps(
        [
            {
                "title": "Nhận laptop",
                "summary": "Nhận laptop tại tầng 12",
                "instructions_markdown": "Nhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR.",
                "done_criteria": ["Đã có laptop"],
                "estimated_minutes": 30,
                "source_chunks": [{"document_section_id": first_section.id, "quote": "Nhận laptop tại tầng 12"}],
                "confidence": "HIGH",
                "warnings": [],
            }
        ]
    )
    app = app_for(session_factory, llm_json)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/ai/task-proposals", json={"document_version_id": result.version_id}
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Nhận laptop"
    assert "completion_mode" not in body[0]


async def test_propose_filters_out_invalid_source_chunk(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[int],
    tmp_path: Path,
) -> None:
    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        result = await _ingest_fixture_document(session, category, hr.email, tmp_path)
    cleanup_documents.append(result.document_id)

    # section_id không tồn tại -> proposal bị loại
    llm_json = json.dumps(
        [
            {
                "title": "Sai section",
                "summary": "x",
                "instructions_markdown": "x",
                "done_criteria": [],
                "estimated_minutes": None,
                "source_chunks": [{"document_section_id": 999999999, "quote": "không tồn tại"}],
                "confidence": "LOW",
                "warnings": [],
            }
        ]
    )
    app = app_for(session_factory, llm_json)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/ai/task-proposals", json={"document_version_id": result.version_id}
        )

    assert response.status_code == 200
    assert response.json() == []


async def test_propose_filters_out_quote_mismatch(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[int],
    tmp_path: Path,
) -> None:
    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        result = await _ingest_fixture_document(session, category, hr.email, tmp_path)
    cleanup_documents.append(result.document_id)

    async with session_factory() as session:
        sections = (
            await session.scalars(select(DocumentSection).where(DocumentSection.version_id == result.version_id))
        ).all()
    first_section = sections[0]

    llm_json = json.dumps(
        [
            {
                "title": "Quote sai",
                "summary": "x",
                "instructions_markdown": "x",
                "done_criteria": [],
                "estimated_minutes": None,
                "source_chunks": [
                    {"document_section_id": first_section.id, "quote": "câu này không có trong tài liệu"}
                ],
                "confidence": "LOW",
                "warnings": [],
            }
        ]
    )
    app = app_for(session_factory, llm_json)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/ai/task-proposals", json={"document_version_id": result.version_id}
        )

    assert response.status_code == 200
    assert response.json() == []


async def test_accept_proposal_creates_task_template_with_source_mapping(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[int],
    cleanup_templates: list[int],
    tmp_path: Path,
) -> None:
    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        result = await _ingest_fixture_document(session, category, hr.email, tmp_path)
    cleanup_documents.append(result.document_id)
    async with session_factory() as session:
        sections = (
            await session.scalars(select(DocumentSection).where(DocumentSection.version_id == result.version_id))
        ).all()
    first_section = sections[0]

    app = app_for(session_factory, "[]")  # không cần LLM cho test này

    async with client_for(app) as client:
        await login(client, hr)
        template_resp = await client.post(
            "/api/v1/portal/journey-templates", json={"code": f"tpl-{uuid4().hex[:8]}", "title": "Lộ trình thử"}
        )
        assert template_resp.status_code == 200, template_resp.text
        template_id = template_resp.json()["id"]
        cleanup_templates.append(template_id)

        stage_resp = await client.post(
            f"/api/v1/portal/journey-templates/{template_id}/stages", json={"title": "Ngày 1", "sort_order": 1}
        )
        assert stage_resp.status_code == 200, stage_resp.text
        stage_id = stage_resp.json()["id"]

        accept_resp = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks/from-proposal",
            json={
                "title": "Nhận laptop",
                "instructions_markdown": "Nhận laptop tại tầng 12.",
                "required": True,
                "source_chunks": [{"document_section_id": first_section.id, "quote": "Nhận laptop tại tầng 12"}],
            },
        )

    assert accept_resp.status_code == 200, accept_resp.text
    task_id = accept_resp.json()["id"]

    async with session_factory() as session:
        mappings = (
            await session.scalars(select(TaskSourceMapping).where(TaskSourceMapping.task_template_id == task_id))
        ).all()
        assert len(mappings) == 1
        assert mappings[0].document_section_id == first_section.id
        assert mappings[0].document_version_id == result.version_id
        assert mappings[0].quote == "Nhận laptop tại tầng 12"  # lưu đoạn trích để "Xem nguồn" tô đúng đoạn


async def test_accepted_proposals_are_ordered_and_linked_by_prerequisites(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[int],
    cleanup_templates: list[int],
    tmp_path: Path,
) -> None:
    from src.model.task_dependency import TaskDependency

    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        result = await _ingest_fixture_document(session, category, hr.email, tmp_path)
    cleanup_documents.append(result.document_id)
    async with session_factory() as session:
        sections = (
            await session.scalars(select(DocumentSection).where(DocumentSection.version_id == result.version_id))
        ).all()
    section = sections[0]

    app = app_for(session_factory, "[]")
    async with client_for(app) as client:
        await login(client, hr)
        template_id = (
            await client.post(
                "/api/v1/portal/journey-templates", json={"code": f"tpl-{uuid4().hex[:8]}", "title": "Lộ trình thử"}
            )
        ).json()["id"]
        cleanup_templates.append(template_id)
        stage_id = (
            await client.post(
                f"/api/v1/portal/journey-templates/{template_id}/stages", json={"title": "Ngày 1", "sort_order": 1}
            )
        ).json()["id"]

        async def accept(title: str, quote: str, depends_on: list[int]) -> int:
            response = await client.post(
                f"/api/v1/portal/stages/{stage_id}/tasks/from-proposal",
                json={
                    "title": title,
                    "instructions_markdown": "Bước 1.",
                    "required": True,
                    "source_chunks": [{"document_section_id": section.id, "quote": quote}],
                    "depends_on": depends_on,
                },
            )
            assert response.status_code == 200, response.text
            return int(response.json()["id"])

        first = await accept("Nhận laptop", "Nhận laptop tại tầng 12", [])
        second = await accept("Đăng ký faceid", "Nhận laptop tại tầng 12", [first])
        bad = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks/from-proposal",
            json={
                "title": "Việc lỗi",
                "instructions_markdown": "x",
                "source_chunks": [{"document_section_id": section.id, "quote": "Nhận laptop tại tầng 12"}],
                "depends_on": [999999999],
            },
        )

    assert bad.status_code == 422  # tiên quyết ngoài lộ trình bị từ chối
    async with session_factory() as session:
        tasks = (
            await session.scalars(
                select(TaskTemplate).where(TaskTemplate.id.in_([first, second])).order_by(TaskTemplate.sort_order)
            )
        ).all()
        assert [task.id for task in tasks] == [first, second]
        assert [task.sort_order for task in tasks] == [1, 2]  # trước đây đều bằng 0
        dependencies = (
            await session.scalars(select(TaskDependency).where(TaskDependency.task_template_id == second))
        ).all()
        assert [dep.depends_on_task_template_id for dep in dependencies] == [first]


async def test_accept_into_published_template_is_rejected(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    cleanup_templates: list[int],
) -> None:
    hr = await make_member("HR", team.id)
    app = app_for(session_factory, "[]")

    async with client_for(app) as client:
        await login(client, hr)
        template_resp = await client.post(
            "/api/v1/portal/journey-templates", json={"code": f"tpl-{uuid4().hex[:8]}", "title": "Lộ trình thử"}
        )
        template_id = template_resp.json()["id"]
        cleanup_templates.append(template_id)
        stage_resp = await client.post(
            f"/api/v1/portal/journey-templates/{template_id}/stages", json={"title": "Ngày 1", "sort_order": 1}
        )
        stage_id = stage_resp.json()["id"]

        async with session_factory() as session:
            await session.execute(
                update(JourneyTemplate)
                .where(JourneyTemplate.id == template_id)
                .values(status=JourneyTemplateStatus.PUBLISHED.value)
            )
            await session.commit()

        response = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks/from-proposal",
            json={"title": "X", "instructions_markdown": "Y", "required": True, "source_chunks": []},
        )

    assert response.status_code == 409
    assert response.json()["code"] == "TEMPLATE_ALREADY_PUBLISHED"
