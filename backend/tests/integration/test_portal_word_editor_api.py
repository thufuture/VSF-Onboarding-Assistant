"""Soạn thảo bản nháp bằng trình soạn thảo kiểu Word (ONLYOFFICE giả bằng httpx.MockTransport), trên PostgreSQL thật."""

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
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
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from test_portal_document_versions_api import upload

from src.api.routers.portal_editor_router import get_onlyoffice_client
from src.config import Settings, get_settings
from src.model.document_version import DocumentVersion
from src.services.portal import word_editor

pytestmark = pytest.mark.integration

SECRET = "test-onlyoffice-secret"
PUBLIC = "http://oo.test:8081"
SETTINGS = {
    "word_editor_enabled": True,
    "onlyoffice_public_url": PUBLIC,
    "onlyoffice_internal_url": "http://oo-internal:80",
    "onlyoffice_backend_url": "http://backend.test:8000",
    "onlyoffice_jwt_secret": SecretStr(SECRET),
}
BODIES = [f"Nội dung điều số {i} có nhiều chữ khác nhau để thành một đoạn riêng. " * 6 for i in range(1, 4)]


def markdown_doc(bodies: list[str]) -> str:
    return "# Quy định thử\n\n" + "\n\n".join(f"## Điều {i}\n\n{b}" for i, b in enumerate(bodies, start=1))


def make_docx(paragraphs: list[tuple[str | None, str]]) -> bytes:
    body = ""
    for style, text in paragraphs:
        ppr = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
        body += f'<w:p>{ppr}<w:r><w:t xml:space="preserve">{text}</w:t></w:r></w:p>'
    document = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?><w:document '
        f'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>{body}</w:body></w:document>'
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'
    )
    rels = (
        '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>'
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


EDITED_DOCX = make_docx(
    [
        ("Heading1", "Quy định thử"),
        ("Heading2", "Điều 1"),
        (None, "Nội dung đã được sửa trong trình soạn thảo Word. " * 8),
    ]
)


class FakeOnlyOffice:
    """Máy chủ ONLYOFFICE giả: ghi lại các lời gọi, trả file chuyển đổi và file đã lưu."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        self.command_error = 0
        self.converted_docx = make_docx([("Heading1", "Dựng từ Markdown"), (None, "Nội dung. " * 40)])

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.method, request.url.path))
        if request.url.path == "/converter":
            body = json.loads(request.content)
            word_editor.jwt_decode(body["token"], SECRET)
            assert request.headers["Authorization"].startswith("Bearer ")
            return httpx.Response(200, json={"endConvert": True, "fileUrl": f"{PUBLIC}/cache/{body['outputtype']}.out"})
        if request.url.path.startswith("/cache/docx"):
            return httpx.Response(200, content=self.converted_docx)
        if request.url.path.startswith("/cache/pdf"):
            return httpx.Response(200, content=b"%PDF-1.7 fake")
        if request.url.path.startswith("/cache/saved"):
            return httpx.Response(200, content=EDITED_DOCX)
        if request.url.path == "/command":
            return httpx.Response(200, json={"error": self.command_error})
        return httpx.Response(404)


@pytest.fixture
def office() -> FakeOnlyOffice:
    return FakeOnlyOffice()


@pytest.fixture
def editor_app(app: FastAPI, office: FakeOnlyOffice, tmp_path: Path) -> FastAPI:
    settings = Settings(_env_file=None, storage_provider="local", storage_path=str(tmp_path), **SETTINGS)  # type: ignore[arg-type]
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_onlyoffice_client] = lambda: word_editor.OnlyOfficeClient(
        settings, transport=httpx.MockTransport(office.handler)
    )
    return app


async def make_draft(client: httpx.AsyncClient, category: str, source_key: str, markdown: str) -> tuple[int, int]:
    created = (await upload(client, category, source_key, label="v1", content=markdown)).json()
    return created["document_id"], created["document_version_id"]


def callback_headers(body: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {word_editor.jwt_encode({'payload': body}, SECRET)}"}


async def test_capabilities_follow_the_flag(
    app: FastAPI, editor_app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await make_member("HR", team.id)
    async with client_for(editor_app) as client:
        await login(client, hr)
        assert (await client.get("/api/v1/portal/capabilities")).json() == {"word_editor": True}
        editor_app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, word_editor_enabled=False)
        assert (await client.get("/api/v1/portal/capabilities")).json() == {"word_editor": False}


async def test_session_is_disabled_by_default_and_only_for_drafts(
    app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None, word_editor_enabled=False)
    async with client_for(app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        response = await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session")
        assert response.status_code == 404 and response.json()["code"] == "EDITOR_DISABLED"


async def test_session_config_is_signed_and_links_are_scoped(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    office: FakeOnlyOffice,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        response = await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session")
        assert response.status_code == 200, response.text
        session = response.json()
        config = session["config"]
        assert session["api_js_url"] == f"{PUBLIC}/web-apps/apps/api/documents/api.js"
        assert config["document"]["fileType"] == "docx" and config["editorConfig"]["lang"] == "vi"
        signed = word_editor.jwt_decode(config["token"], SECRET)
        assert signed["document"]["key"] == session["document_key"]

        # Liên kết lấy file: HTML dựng từ Markdown có tiêu đề; mã "callback" không dùng để lấy file.
        doc_url = config["document"]["url"]
        token = doc_url.rsplit("/", 1)[1]
        html_token = word_editor.make_link_token(
            Settings(_env_file=None, **SETTINGS),  # type: ignore[arg-type]
            version_id=version_id,
            kind="html",
            user_id=1,
        )
        html = await client.get(f"/api/v1/portal/editor-files/{html_token}")
        assert html.status_code == 200 and "<h2>Điều 1</h2>" in html.text
        callback_token = config["editorConfig"]["callbackUrl"].rsplit("/", 1)[1]
        assert (await client.get(f"/api/v1/portal/editor-files/{callback_token}")).status_code == 403
        assert (await client.get(f"/api/v1/portal/editor-files/{token}x")).status_code == 403

        # File .docx: chưa có file Word nên dựng từ Markdown qua bộ chuyển đổi (tải file không cần cookie đăng nhập).
        docx = await client.get(f"/api/v1/portal/editor-files/{token}")
        assert docx.status_code == 200 and docx.content == office.converted_docx
        assert ("POST", "/converter") in office.calls


async def open_session(client: httpx.AsyncClient, doc_id: int, version_id: int) -> tuple[str, str]:
    """Mở phiên soạn thảo; trả (đường dẫn callback, đường dẫn lưu)."""
    base = f"/api/v1/portal/documents/{doc_id}/versions/{version_id}"
    config = (await client.post(f"{base}/editor-session")).json()["config"]
    token = config["editorConfig"]["callbackUrl"].rsplit("/", 1)[1]
    return f"/api/v1/portal/editor-callback/{token}", f"{base}/editor-session/save"


async def test_save_as_pdf_stores_markdown_working_docx_and_pdf_original(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    office: FakeOnlyOffice,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        path, save_path = await open_session(client, doc_id, version_id)

        opening = {"key": "k", "status": 1, "users": ["1"]}
        assert (await client.post(path, json=opening, headers=callback_headers(opening))).json() == {"error": 0}

        # HR bấm Lưu và chọn PDF: dấu chờ lưu được đặt, rồi ONLYOFFICE gửi file về.
        saved_reply = await client.post(save_path, json={"document_key": "k", "format": "pdf"})
        assert saved_reply.json() == {"ok": True, "changed": True}
        saved = {"key": "k", "status": 6, "url": f"{PUBLIC}/cache/saved/output.docx"}
        done = await client.post(path, json=saved, headers=callback_headers(saved))
        assert done.json() == {"error": 0}

        async with session_factory() as session:
            version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert version is not None
            assert "đã được sửa trong trình soạn thảo Word" in version.markdown
            assert version.source == "EDITED"
            assert word_editor.PENDING_SAVE_KEY not in version.quality_report
            # File gốc là PDF xuất từ bản Word; bản làm việc .docx lưu riêng.
            assert version.original_filename == "v1.pdf" and version.mime_type == "application/pdf"
            assert word_editor.working_docx_key(version) is not None
            assert word_editor.working_docx_key(version) != version.storage_key

        # Mở lại: dùng bản làm việc đã lưu (giữ nguyên định dạng Word), không dựng lại từ Markdown.
        calls_before = len(office.calls)
        again = (await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session")).json()
        token = again["config"]["document"]["url"].rsplit("/", 1)[1]
        docx = await client.get(f"/api/v1/portal/editor-files/{token}")
        assert docx.content == EDITED_DOCX
        assert len(office.calls) == calls_before

        # "Xem file gốc": PDF mở thẳng trong trình duyệt.
        original = await client.get(f"/api/v1/portal/documents/{version_id}/original")
        assert original.status_code == 200 and original.content.startswith(b"%PDF")
        assert original.headers["content-disposition"].startswith("inline")


async def test_save_as_markdown_makes_the_markdown_file_the_original(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        path, save_path = await open_session(client, doc_id, version_id)
        assert (await client.post(save_path, json={"document_key": "k", "format": "markdown"})).json()["ok"] is True
        saved = {"key": "k", "status": 2, "url": f"{PUBLIC}/cache/saved/output.docx"}
        assert (await client.post(path, json=saved, headers=callback_headers(saved))).json() == {"error": 0}

        async with session_factory() as session:
            version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert version is not None
            assert version.original_filename == "v1.md" and version.mime_type == "text/markdown"
            markdown = version.markdown
        original = await client.get(f"/api/v1/portal/documents/{version_id}/original")
        assert original.content.decode("utf-8") == markdown


async def test_save_as_word_keeps_the_word_file_as_the_original(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        path, save_path = await open_session(client, doc_id, version_id)
        assert (await client.post(save_path, json={"document_key": "k", "format": "docx"})).json()["ok"] is True
        saved = {"key": "k", "status": 2, "url": f"{PUBLIC}/cache/saved/output.docx"}
        assert (await client.post(path, json=saved, headers=callback_headers(saved))).json() == {"error": 0}

        async with session_factory() as session:
            version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert version is not None
            assert version.original_filename == "v1.docx" and version.mime_type == word_editor.DOCX_MIME
        original = await client.get(f"/api/v1/portal/documents/{version_id}/original")
        assert original.content == EDITED_DOCX


async def test_cancel_discards_changes_because_nothing_is_written_without_save(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    office: FakeOnlyOffice,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        path, _ = await open_session(client, doc_id, version_id)
        async with session_factory() as session:
            before = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert before is not None
            markdown_before, file_before = before.markdown, before.file_checksum

        # HR sửa rồi bấm Hủy: ONLYOFFICE vẫn gửi file lúc đóng, nhưng không có lệnh Lưu nên bị bỏ qua (không tải, không ghi).
        closing = {"key": "k", "status": 2, "url": f"{PUBLIC}/cache/saved/output.docx"}
        assert (await client.post(path, json=closing, headers=callback_headers(closing))).json() == {"error": 0}

        async with session_factory() as session:
            after = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
            assert after is not None
            assert after.markdown == markdown_before and after.file_checksum == file_before
        assert not any(call[1].startswith("/cache/saved") for call in office.calls)


async def test_save_without_changes_clears_the_pending_mark(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    office: FakeOnlyOffice,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    office.command_error = 4
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        _, save_path = await open_session(client, doc_id, version_id)
        reply = await client.post(save_path, json={"document_key": "k", "format": "pdf"})
        assert reply.json() == {"ok": True, "changed": False}
    async with session_factory() as session:
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
        assert version is not None and word_editor.PENDING_SAVE_KEY not in version.quality_report


async def test_callback_rejects_forged_requests_and_foreign_hosts(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        config = (await client.post(f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session")).json()[
            "config"
        ]
        token = config["editorConfig"]["callbackUrl"].rsplit("/", 1)[1]
        path = f"/api/v1/portal/editor-callback/{token}"
        saved = {"key": "k", "status": 2, "url": f"{PUBLIC}/cache/saved/output.docx"}

        assert (await client.post(path + "x", json=saved, headers=callback_headers(saved))).status_code == 403
        no_jwt = await client.post(path, json=saved)
        assert no_jwt.status_code == 403
        bad_jwt = await client.post(path, json=saved, headers={"Authorization": "Bearer abc.def.ghi"})
        assert bad_jwt.status_code == 403

        save_path = f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session/save"
        await client.post(save_path, json={"document_key": "k", "format": "pdf"})
        foreign = {"key": "k", "status": 2, "url": "http://169.254.169.254/latest/meta-data"}
        assert (await client.post(path, json=foreign, headers=callback_headers(foreign))).json() == {"error": 1}

    async with session_factory() as session:
        version = await session.scalar(select(DocumentVersion).where(DocumentVersion.id == version_id))
        assert version is not None and version.markdown == markdown_doc(BODIES).strip() or version.source == "UPLOAD"


async def test_export_pdf_and_docx_and_forcesave(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
    office: FakeOnlyOffice,
) -> None:
    hr = await make_member("HR", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
        base = f"/api/v1/portal/documents/{doc_id}/versions/{version_id}"
        pdf = await client.get(f"{base}/export?format=pdf")
        assert (
            pdf.status_code == 200
            and pdf.content.startswith(b"%PDF")
            and pdf.headers["content-type"] == "application/pdf"
        )
        docx = await client.get(f"{base}/export?format=docx")
        assert docx.status_code == 200 and docx.content == office.converted_docx
        save = await client.post(f"{base}/editor-session/save", json={"document_key": "k", "format": "pdf"})
        assert save.json() == {"ok": True, "changed": True}
        assert ("POST", "/command") in office.calls


async def test_editor_endpoints_require_staff(
    editor_app: FastAPI,
    team: SimpleNamespace,
    category: str,
    make_member: MakeMember,
    cleanup_documents: list[str],
) -> None:
    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)
    source_key = f"ed-{uuid4().hex[:10]}"
    cleanup_documents.append(source_key)
    async with client_for(editor_app) as client:
        await login(client, hr)
        doc_id, version_id = await make_draft(client, category, source_key, markdown_doc(BODIES))
    async with client_for(editor_app) as client:
        await login(client, employee)
        assert (await client.get("/api/v1/portal/capabilities")).status_code == 403
        url = f"/api/v1/portal/documents/{doc_id}/versions/{version_id}/editor-session"
        assert (await client.post(url)).status_code == 403
