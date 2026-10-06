"""Tích hợp 2-B trên PostgreSQL thật: nạp SYN_D03b bằng FakeEmbeddingAdapter + LocalStorageAdapter,
kiểm số section/chunk > 0, INV14 (chunk cùng version với section cha), INV5 (idempotent theo checksum).

Kế hoạch: docs/chatbot-vsf/plan/phase-2/2-b-nap-tai-lieu-ke-hoach-chi-tiet.md, mục 8.
"""

from collections.abc import AsyncIterator
from datetime import date
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.persistence.engine import create_session_factory
from src.model.audit_log import AuditLog
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.user import User
from src.services.auth.passwords import hash_password
from src.services.ingest.embedding.fake_adapter import FakeEmbeddingAdapter
from src.services.ingest.ingest_service import IngestError, ingest_document
from src.services.ingest.storage import LocalStorageAdapter

pytestmark = pytest.mark.integration

_REPO_ROOT = Path(__file__).resolve().parents[3]
_D03B = (
    _REPO_ROOT
    / "docs"
    / "chatbot-vsf"
    / "data"
    / "documents"
    / "core"
    / ("SYN_D03b_Chinh_sach_nghi_phep_nam_v2024.docx")
)


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def owner(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[Any]:
    """Một người dùng HR tạm để làm owner_id/uploaded_by, dọn sạch sau test (không phụ thuộc registry seed)."""
    from types import SimpleNamespace

    email = f"ingest-test-{uuid4().hex[:10]}@example.test"
    async with session_factory() as session:
        user = User(email=email, display_name="HR Thử", role="HR", password_hash=hash_password("ChangeMe!123"))
        session.add(user)
        await session.commit()
        result = SimpleNamespace(email=email, id=user.id)
    yield result
    async with session_factory() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.commit()


@pytest.fixture
async def category(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[str]:
    """Một danh mục tạm, dọn sạch sau test."""
    slug = f"ingest-test-{uuid4().hex[:8]}"
    async with session_factory() as session:
        session.add(DocumentCategory(slug=slug, name="Danh mục thử"))
        await session.commit()
    yield slug
    async with session_factory() as session:
        await session.execute(delete(DocumentCategory).where(DocumentCategory.slug == slug))
        await session.commit()


@pytest.fixture
async def cleanup_document(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[list[str]]:
    """Xóa document theo source_key sau test (kèm version/section/chunk/audit_log phụ thuộc, INV14)."""
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
                await session.execute(
                    delete(AuditLog).where(
                        AuditLog.entity_type == "document_version",
                        AuditLog.entity_id.in_([str(v) for v in version_ids]),
                    )
                )
                await session.execute(delete(DocumentVersion).where(DocumentVersion.id.in_(version_ids)))
            await session.execute(delete(Document).where(Document.id == document.id))
        await session.commit()


async def test_ingest_creates_document_version_sections_and_chunks(
    session_factory: async_sessionmaker[AsyncSession],
    owner: Any,
    category: str,
    cleanup_document: list[str],
    tmp_path: Path,
) -> None:
    source_key = f"src-{uuid4().hex[:10]}"
    cleanup_document.append(source_key)

    async with session_factory() as session:
        result = await ingest_document(
            session,
            file_path=_D03B,
            category_slug=category,
            owner_email=owner.email,
            title="Chính sách nghỉ phép năm (thử nghiệm)",
            source_key=source_key,
            version_label="1.0",
            effective_from=date(2024, 1, 1),
            content_kind="GENERAL",
            confidentiality="INTERNAL",
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )

    assert result.created is True
    assert result.section_count > 0
    assert result.chunk_count > 0

    async with session_factory() as session:
        document = await session.get(Document, result.document_id)
        assert document is not None
        assert document.source_key == source_key

        version = await session.get(DocumentVersion, result.version_id)
        assert version is not None
        assert version.status == "ACTIVE"
        assert version.embedding_model_version == FakeEmbeddingAdapter.model_version
        assert version.storage_key  # LocalStorageAdapter đã ghi file và trả đường dẫn tương đối

        sections = (
            await session.scalars(select(DocumentSection).where(DocumentSection.version_id == result.version_id))
        ).all()
        chunks = (
            await session.scalars(select(DocumentChunk).where(DocumentChunk.version_id == result.version_id))
        ).all()

        assert len(sections) == result.section_count
        assert len(chunks) == result.chunk_count

        section_ids = {s.id for s in sections}
        for chunk in chunks:
            # INV14: mọi chunk phải thuộc một section cùng version (không trỏ nhầm section của version khác).
            assert chunk.section_id in section_ids
            assert chunk.embedding is not None
            assert len(chunk.embedding) == FakeEmbeddingAdapter.dimension
            assert chunk.lexical_text
            assert chunk.content_hash


async def test_reingesting_same_content_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
    owner: Any,
    category: str,
    cleanup_document: list[str],
    tmp_path: Path,
) -> None:
    source_key = f"src-{uuid4().hex[:10]}"
    cleanup_document.append(source_key)

    async def ingest_once() -> Any:
        async with session_factory() as session:
            return await ingest_document(
                session,
                file_path=_D03B,
                category_slug=category,
                owner_email=owner.email,
                title="Chính sách nghỉ phép năm (thử nghiệm)",
                source_key=source_key,
                version_label="1.0",
                effective_from=date(2024, 1, 1),
                content_kind="GENERAL",
                confidentiality="INTERNAL",
                embedding=FakeEmbeddingAdapter(),
                storage=LocalStorageAdapter(str(tmp_path)),
            )

    first = await ingest_once()
    second = await ingest_once()

    assert first.created is True
    assert second.created is False
    assert first.version_id == second.version_id
    assert first.chunk_count == second.chunk_count

    async with session_factory() as session:
        versions = (
            await session.scalars(select(DocumentVersion).where(DocumentVersion.document_id == first.document_id))
        ).all()
        assert len(versions) == 1  # không nhân đôi (INV5)


async def test_same_version_label_different_content_is_rejected(
    session_factory: async_sessionmaker[AsyncSession],
    owner: Any,
    category: str,
    cleanup_document: list[str],
    tmp_path: Path,
) -> None:
    source_key = f"src-{uuid4().hex[:10]}"
    cleanup_document.append(source_key)

    other_doc = tmp_path / "khac.md"
    other_doc.write_text("# Tài liệu khác\n\n" + "Nội dung hoàn toàn khác D03b. " * 30, encoding="utf-8")

    async with session_factory() as session:
        await ingest_document(
            session,
            file_path=_D03B,
            category_slug=category,
            owner_email=owner.email,
            title="Bản gốc",
            source_key=source_key,
            version_label="1.0",
            effective_from=date(2024, 1, 1),
            content_kind="GENERAL",
            confidentiality="INTERNAL",
            embedding=FakeEmbeddingAdapter(),
            storage=LocalStorageAdapter(str(tmp_path)),
        )

    with pytest.raises(IngestError, match="INV5"):
        async with session_factory() as session:
            await ingest_document(
                session,
                file_path=other_doc,
                category_slug=category,
                owner_email=owner.email,
                title="Bản gốc",
                source_key=source_key,
                version_label="1.0",  # cùng nhãn phiên bản, nội dung khác -> phải bị từ chối (INV5)
                effective_from=date(2024, 1, 1),
                content_kind="GENERAL",
                confidentiality="INTERNAL",
                embedding=FakeEmbeddingAdapter(),
                storage=LocalStorageAdapter(str(tmp_path)),
            )


async def test_missing_category_raises_clear_error(
    session_factory: async_sessionmaker[AsyncSession],
    owner: Any,
    tmp_path: Path,
) -> None:
    async with session_factory() as session:
        with pytest.raises(IngestError, match="danh mục"):
            await ingest_document(
                session,
                file_path=_D03B,
                category_slug="danh-muc-khong-ton-tai",
                owner_email=owner.email,
                title="Bất kỳ",
                source_key=f"src-{uuid4().hex[:10]}",
                version_label="1.0",
                effective_from=date(2024, 1, 1),
                content_kind="GENERAL",
                confidentiality="INTERNAL",
                embedding=FakeEmbeddingAdapter(),
                storage=LocalStorageAdapter(str(tmp_path)),
            )
