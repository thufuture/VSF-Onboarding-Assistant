"""HR upload tài liệu qua `/api/v1/portal/documents` trên PostgreSQL thật (plan-portal/P4B/P4B.md mục 8.3, 8.6).

Dùng `FakeEmbeddingAdapter` (không gọi mạng) + `LocalStorageAdapter` (ghi vào thư mục tạm của test).
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.dependencies import get_embedding_port, get_storage_port
from src.config import Settings, get_settings
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.storage import LocalStorageAdapter

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"
_MD_CONTENT = "# Tài liệu thử\n\n" + "Nội dung dùng để test upload qua API Portal. " * 20

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
    slug = f"portal-test-{uuid4().hex[:8]}"
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục thử Portal"))
        await session.commit()
    yield slug
    async with session_factory() as session:
        await session.execute(delete(DocumentCategory).where(DocumentCategory.slug == slug))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-upload-{uuid4().hex[:10]}@example.test"
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


@pytest.fixture
async def cleanup_documents(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[list[str]]:
    source_keys: list[str] = []
    yield source_keys
    if not source_keys:
        return
    async with session_factory() as session:
        for key in source_keys:
            document = await session.scalar(select(Document).where(Document.source_key == key))
            if document is None:
                continue
            version_ids = list(
                (
                    await session.scalars(select(DocumentVersion.id).where(DocumentVersion.document_id == document.id))
                ).all()
            )
            if version_ids:
                await session.execute(delete(DocumentChunk).where(DocumentChunk.version_id.in_(version_ids)))
                await session.execute(delete(DocumentSection).where(DocumentSection.version_id.in_(version_ids)))
                await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
            await session.execute(delete(Document).where(Document.id == document.id))
        await session.commit()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession], tmp_path: Path) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(3, 900)
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_embedding_port] = lambda: FakeEmbeddingAdapter()
    application.dependency_overrides[get_storage_port] = lambda: LocalStorageAdapter(str(tmp_path))
    return application


def client_for(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("10.0.0.1", 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def login(client: httpx.AsyncClient, user: SimpleNamespace) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})


def _upload_form(category_slug: str, source_key: str) -> dict[str, str]:
    return {
        "title": "Tài liệu thử",
        "category_slug": category_slug,
        "source_key": source_key,
        "version_label": "1.0",
        "effective_from": "2024-01-01",
    }


async def test_hr_uploads_document(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.post(
            "/api/v1/portal/documents",
            data=_upload_form(category, source_key),
            files={"file": ("test.md", _MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] is True
    assert body["section_count"] >= 1
    assert body["chunk_count"] >= 1


async def test_user_role_cannot_upload(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        response = await client.post(
            "/api/v1/portal/documents",
            data=_upload_form(category, f"upload-{uuid4().hex[:10]}"),
            files={"file": ("test.md", _MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


async def test_reupload_same_content_is_idempotent(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"upload-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    form = _upload_form(category, source_key)

    async with client_for(app) as client:
        await login(client, hr)
        first = await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", _MD_CONTENT.encode("utf-8"), "text/markdown")},
        )
        second = await client.post(
            "/api/v1/portal/documents",
            data=form,
            files={"file": ("test.md", _MD_CONTENT.encode("utf-8"), "text/markdown")},
        )

    assert first.json()["created"] is True
    assert second.json()["created"] is False
    assert first.json()["document_version_id"] == second.json()["document_version_id"]
