"""Soạn thảo bản nháp bằng trình soạn thảo kiểu Word (ONLYOFFICE Docs), tắt mặc định (`WORD_EDITOR_ENABLED`).

Luồng: HR mở bản nháp trong trình soạn thảo, ONLYOFFICE gọi lại backend khi lưu, backend tải file .docx về, đọc thành Markdown (cùng
bộ đọc `parse_document` như khi tải file lên), lưu file .docx làm "file gốc" của bản nháp và cập nhật Markdown. Kích hoạt sau đó
chạy như cũ (cắt đoạn, embedding), nên chỉ phần đã sửa phải tính lại khi bật `EMBEDDING_CACHE_ENABLED`.

Bảo mật: ONLYOFFICE chỉ nói chuyện với backend qua các đường dẫn có **mã ký ngắn hạn** (gắn với đúng một phiên bản và một người
dùng) và JWT dùng chung; URL file trong callback phải trỏ về chính máy chủ ONLYOFFICE đã cấu hình (chống SSRF).
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import json
import logging
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlsplit, urlunsplit

import httpx
from markdown_it import MarkdownIt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import Settings
from src.model.audit_log import AuditLog
from src.model.document_version import DocumentVersion
from src.model.enums import VersionSource, VersionStatus
from src.model.user import User
from src.services.ingest.markdown_patch import patch_markdown
from src.services.ingest.parser import MAX_FILE_SIZE_BYTES, ParseError, parse_document
from src.services.ingest.pdf_to_docx import PdfToWordError, convert_pdf_to_docx
from src.services.ingest.storage import StoragePort
from src.services.ingest.structure import analyze_structure
from src.services.ingest.version_lifecycle import checksum_of
from src.services.portal.errors import PortalError

logger = logging.getLogger(__name__)

DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
LINK_TTL_SECONDS = 12 * 3600
# ONLYOFFICE callback: 2 = đã đóng và có file để lưu, 6 = lưu ngay (forcesave); các mã khác không có file mới.
SAVE_STATUSES = frozenset({2, 6})
DOCX_CHECKSUM_KEY = "docx_content_checksum"  # cách ghi cũ, còn đọc được
WORKING_DOCX_KEY = "working_docx"
PENDING_SAVE_KEY = "pending_save"
SaveFormat = Literal["docx", "pdf", "markdown"]


class InvalidTokenError(Exception):
    pass


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def jwt_encode(payload: dict[str, Any], secret: str) -> str:
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
    return f"{head}.{body}.{signature}"


def jwt_decode(token: str, secret: str) -> dict[str, Any]:
    try:
        head, body, signature = token.split(".")
        expected = _b64(hmac.new(secret.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected) or json.loads(_unb64(head)).get("alg") != "HS256":
            raise InvalidTokenError("sai chữ ký")
        payload = json.loads(_unb64(body))
    except (ValueError, KeyError) as exc:
        raise InvalidTokenError("token hỏng") from exc
    if not isinstance(payload, dict):
        raise InvalidTokenError("token hỏng")
    if "exp" in payload and float(payload["exp"]) < time.time():
        raise InvalidTokenError("token hết hạn")
    return payload


def _secret(settings: Settings) -> str:
    return settings.onlyoffice_jwt_secret.get_secret_value() if settings.onlyoffice_jwt_secret else ""


def require_enabled(settings: Settings) -> None:
    configured = all(
        [
            settings.word_editor_enabled,
            settings.onlyoffice_public_url,
            settings.onlyoffice_internal_url,
            settings.onlyoffice_backend_url,
            _secret(settings),
        ]
    )
    if not configured:
        raise PortalError(404, "EDITOR_DISABLED", "portal.editor_disabled")


def make_link_token(settings: Settings, *, version_id: int, kind: str, user_id: int) -> str:
    return jwt_encode(
        {"v": version_id, "k": kind, "u": user_id, "exp": int(time.time()) + LINK_TTL_SECONDS}, _secret(settings)
    )


def read_link_token(settings: Settings, token: str, *, kind: str) -> tuple[int, int]:
    """Trả (mã phiên bản, mã người dùng); sai loại, hết hạn hay giả mạo đều từ chối."""
    try:
        payload = jwt_decode(token, _secret(settings))
        if payload.get("k") != kind:
            raise InvalidTokenError("sai loại")
        return int(payload["v"]), int(payload["u"])
    except (InvalidTokenError, KeyError, ValueError) as exc:
        raise PortalError(403, "EDITOR_LINK_INVALID", "portal.editor_link_invalid") from exc


def markdown_to_html(markdown: str) -> str:
    body = MarkdownIt("commonmark", {"html": False}).enable("table").render(markdown)
    return f"<!doctype html><html><head><meta charset='utf-8'></head><body>{body}</body></html>"


def document_key(version: DocumentVersion) -> str:
    """Khóa phiên bản của ONLYOFFICE: đổi khi nội dung đổi để không dùng nhầm bản nhớ đệm cũ."""
    raw = f"{version.id}:{version.content_checksum}:{version.file_checksum}:{version.updated_at.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:40]


def working_docx_key(version: DocumentVersion) -> str | None:
    """Nơi lưu file .docx làm việc (dùng để mở trình soạn thảo) nếu còn khớp nội dung hiện tại, không thì None.

    File gốc của phiên bản (PDF, Markdown hay Word do HR chọn khi lưu) là chuyện khác: bản làm việc lưu riêng để file gốc không đổi
    chỉ vì mở trình soạn thảo."""
    working = version.quality_report.get(WORKING_DOCX_KEY)
    if isinstance(working, dict):
        if working.get("content_checksum") == version.content_checksum and working.get("storage_key"):
            return str(working["storage_key"])
        return None
    if version.original_filename.lower().endswith(".docx"):
        marker = version.quality_report.get(DOCX_CHECKSUM_KEY)
        if marker is not None:
            return version.storage_key if marker == version.content_checksum else None
        # Tải lên file .docx và chưa sửa: file gốc chính là bản làm việc.
        return version.storage_key if version.source == VersionSource.UPLOAD.value else None
    return None


def stored_docx_is_current(version: DocumentVersion) -> bool:
    return working_docx_key(version) is not None


def working_docx_for_copy(source: DocumentVersion) -> dict[str, str] | None:
    """Bản sao dùng chung file .docx làm việc của bản nguồn nếu file đó còn khớp nội dung."""
    key = working_docx_key(source)
    if key is None:
        return None
    return {"storage_key": key, "content_checksum": source.content_checksum}


def pending_save_format(version: DocumentVersion) -> SaveFormat | None:
    """Định dạng file gốc HR đã chọn ở hộp "Lưu"; có giá trị thì lần ONLYOFFICE gửi file tới mới được ghi, không thì bỏ qua (Hủy)."""
    pending = version.quality_report.get(PENDING_SAVE_KEY)
    fmt = pending.get("format") if isinstance(pending, dict) else None
    return fmt if fmt in ("docx", "pdf", "markdown") else None


async def set_pending_save(session: AsyncSession, version: DocumentVersion, fmt: SaveFormat | None) -> None:
    report = {k: v for k, v in version.quality_report.items() if k != PENDING_SAVE_KEY}
    if fmt is not None:
        report[PENDING_SAVE_KEY] = {"format": fmt}
    version.quality_report = report
    await session.commit()
    await session.refresh(version)


class OnlyOfficeClient:
    """Gọi ONLYOFFICE từ backend: chuyển đổi định dạng, tải file kết quả, lệnh lưu."""

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._secret = _secret(settings)
        self._internal = urlsplit(settings.onlyoffice_internal_url)
        self._public = urlsplit(settings.onlyoffice_public_url)
        self._transport = transport

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transport, timeout=120)

    def _signed(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = jwt_encode(payload, self._secret)
        return {
            "json": {**payload, "token": token},
            "headers": {"Authorization": f"Bearer {token}", "Accept": "application/json"},
        }

    def internal_url(self, url: str) -> str:
        """ONLYOFFICE ghi URL theo địa chỉ công khai của nó; backend phải gọi qua địa chỉ nội bộ."""
        parts = urlsplit(url)
        if parts.netloc not in {self._public.netloc, self._internal.netloc}:
            raise PortalError(400, "EDITOR_CALLBACK_URL", "portal.editor_callback_url")
        return urlunsplit(parts._replace(scheme=self._internal.scheme, netloc=self._internal.netloc))

    async def convert(self, *, source_url: str, filetype: str, outputtype: str, key: str) -> bytes:
        payload = {
            "async": False,
            "filetype": filetype,
            "key": key,
            "outputtype": outputtype,
            "title": f"tai-lieu.{filetype}",
            "url": source_url,
        }
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self._internal.geturl()}/converter",
                    **self._signed(payload),
                )
                response.raise_for_status()
                result = response.json()
                if not result.get("endConvert") or not result.get("fileUrl"):
                    raise PortalError(502, "EDITOR_CONVERT_FAILED", "portal.editor_convert_failed")
                return await self._download(client, str(result["fileUrl"]))
        except httpx.HTTPError as exc:
            raise PortalError(502, "EDITOR_UNAVAILABLE", "portal.editor_unavailable") from exc

    async def _download(self, client: httpx.AsyncClient, url: str) -> bytes:
        target = self.internal_url(url)
        response = await client.get(
            target, headers={"Authorization": f"Bearer {jwt_encode({'url': target}, self._secret)}"}
        )
        response.raise_for_status()
        if len(response.content) > MAX_FILE_SIZE_BYTES:
            raise PortalError(413, "EDITOR_FILE_TOO_LARGE", "portal.editor_file_too_large")
        return response.content

    async def download(self, url: str) -> bytes:
        try:
            async with self._client() as client:
                return await self._download(client, url)
        except httpx.HTTPError as exc:
            raise PortalError(502, "EDITOR_UNAVAILABLE", "portal.editor_unavailable") from exc

    async def command(self, name: str, key: str) -> dict[str, Any]:
        try:
            async with self._client() as client:
                response = await client.post(
                    f"{self._internal.geturl()}/command", **self._signed({"c": name, "key": key})
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as exc:
            raise PortalError(502, "EDITOR_UNAVAILABLE", "portal.editor_unavailable") from exc
        return data if isinstance(data, dict) else {}


async def _read_stored_file(storage_key: str, settings: Settings) -> bytes:
    if settings.storage_provider == "cloudinary":
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.get(storage_key)
            response.raise_for_status()
            return response.content
    return await asyncio.to_thread((Path(settings.storage_path) / storage_key).read_bytes)


async def read_stored_file(storage_key: str, settings: Settings) -> bytes:
    return await _read_stored_file(storage_key, settings)


async def docx_bytes_for(
    version: DocumentVersion, settings: Settings, client: OnlyOfficeClient, *, user_id: int
) -> bytes:
    """File .docx để mở/xuất: dùng file đang lưu nếu còn khớp nội dung (giữ nguyên định dạng Word), nếu không dựng từ Markdown."""
    key = working_docx_key(version)
    if key is not None:
        try:
            return await _read_stored_file(key, settings)
        except (OSError, httpx.HTTPError) as exc:
            logger.warning(
                "editor_stored_file_unreadable version=%s error=%s", version.id, type(exc).__name__
            )  # mất file thì dựng lại từ Markdown, vẫn đủ nội dung chữ
    html_token = make_link_token(settings, version_id=version.id, kind="html", user_id=user_id)
    url = f"{settings.onlyoffice_backend_url.rstrip('/')}/api/v1/portal/editor-files/{html_token}"
    return await client.convert(
        source_url=url, filetype="html", outputtype="docx", key=f"h{document_key(version)}{int(time.time())}"
    )


def is_pdf_original(version: DocumentVersion) -> bool:
    return version.mime_type == "application/pdf" or version.original_filename.lower().endswith(".pdf")


async def _markdown_of_docx(content: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(content)
        path = Path(tmp.name)
    try:
        return (await asyncio.to_thread(parse_document, path)).markdown
    finally:
        path.unlink(missing_ok=True)


async def _store_text(storage: StoragePort, text: str) -> str:
    data = text.encode("utf-8")
    return await storage.store(data, checksum=hashlib.sha256(data).hexdigest(), filename="baseline.md")


async def _working_from_pdf(
    version: DocumentVersion, settings: Settings, storage: StoragePort
) -> dict[str, str] | None:
    """PDF gốc -> Word giữ bố cục (pdf2docx), kèm bản Markdown "mốc" B0 đọc từ chính bản Word đó để sau này biết HR sửa chỗ nào.
    Trả None (dùng đường dựng từ Markdown) khi tính năng tắt, không phải PDF, hay không chuyển được."""
    if not settings.pdf_to_word_enabled or not is_pdf_original(version) or version.quality_report.get("ocr"):
        return None  # bản đã OCR: PDF là ảnh kèm lớp chữ vô hình, pdf2docx không dựng lại thành đoạn văn được
    try:
        pdf = await _read_stored_file(version.storage_key, settings)
        docx = await asyncio.to_thread(convert_pdf_to_docx, pdf, max_pages=settings.pdf_to_word_max_pages)
        baseline = await _markdown_of_docx(docx)
    except (PdfToWordError, ParseError, OSError, httpx.HTTPError) as exc:
        logger.warning("pdf_to_word_failed version=%s error=%s", version.id, type(exc).__name__)
        return None
    try:
        docx_key = await storage.store(docx, checksum=hashlib.sha256(docx).hexdigest(), filename="tai-lieu.docx")
        baseline_key = await _store_text(storage, baseline)
    except Exception as exc:
        raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc
    return {"storage_key": docx_key, "content_checksum": version.content_checksum, "baseline_key": baseline_key}


async def ensure_docx_file(
    session: AsyncSession,
    version: DocumentVersion,
    settings: Settings,
    client: OnlyOfficeClient,
    storage: StoragePort,
    *,
    user_id: int,
) -> None:
    """Bảo đảm bản nháp đã có file .docx khớp nội dung TRƯỚC khi mở trình soạn thảo (dựng từ Markdown nếu chưa có).

    Phải làm ở đây chứ không trong lúc ONLYOFFICE đang tải file: máy chủ ONLYOFFICE đang chờ ta trả file thì không chuyển đổi
    được (đo thật: lời gọi chuyển đổi lồng bên trong bị quá giờ). File dựng ra là bản làm việc; file gốc của bản nháp không đổi."""
    if working_docx_key(version) is not None:
        return
    working = await _working_from_pdf(version, settings, storage)
    if working is None:
        html_token = make_link_token(settings, version_id=version.id, kind="html", user_id=user_id)
        url = f"{settings.onlyoffice_backend_url.rstrip('/')}/api/v1/portal/editor-files/{html_token}"
        content = await client.convert(
            source_url=url, filetype="html", outputtype="docx", key=f"h{document_key(version)}{int(time.time())}"
        )
        checksum = hashlib.sha256(content).hexdigest()
        try:
            storage_key = await storage.store(content, checksum=checksum, filename="tai-lieu.docx")
        except Exception as exc:
            raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc
        working = {"storage_key": storage_key, "content_checksum": version.content_checksum}
    version.quality_report = {**version.quality_report, WORKING_DOCX_KEY: working}
    await session.commit()
    await session.refresh(version)


async def stored_docx_bytes(version: DocumentVersion, settings: Settings) -> bytes:
    key = working_docx_key(version)
    if key is None:
        raise PortalError(409, "EDITOR_FILE_NOT_READY", "portal.editor_file_not_ready")
    try:
        return await _read_stored_file(key, settings)
    except (OSError, httpx.HTTPError) as exc:
        logger.warning("editor_stored_file_unreadable version=%s error=%s", version.id, type(exc).__name__)
        raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc


@dataclass(frozen=True)
class EditorSession:
    api_js_url: str
    config: dict[str, Any]
    document_key: str


def build_session(version: DocumentVersion, settings: Settings, user: User) -> EditorSession:
    docx_token = make_link_token(settings, version_id=version.id, kind="docx", user_id=user.id)
    callback_token = make_link_token(settings, version_id=version.id, kind="callback", user_id=user.id)
    backend = settings.onlyoffice_backend_url.rstrip("/")
    key = document_key(version)
    config: dict[str, Any] = {
        "documentType": "word",
        "document": {
            "fileType": "docx",
            "key": key,
            "title": f"{version.version_label}.docx",
            "url": f"{backend}/api/v1/portal/editor-files/{docx_token}",
            "permissions": {"edit": True, "download": True, "print": True, "review": True},
        },
        "editorConfig": {
            "mode": "edit",
            "lang": "vi",
            "callbackUrl": f"{backend}/api/v1/portal/editor-callback/{callback_token}",
            "user": {"id": str(user.id), "name": user.display_name},
            "customization": {
                "forcesave": True,
                "autosave": True,
                # Gọn đầu trình soạn thảo: gộp thanh menu vào dòng tiêu đề, bỏ tên file và ngăn phải để nhường chỗ cho trang giấy.
                "compactHeader": True,
                "toolbarHideFileName": True,
                "hideRightMenu": True,
            },
        },
        "height": "100%",
        "width": "100%",
    }
    config["token"] = jwt_encode(config, _secret(settings))
    return EditorSession(
        api_js_url=f"{settings.onlyoffice_public_url.rstrip('/')}/web-apps/apps/api/documents/api.js",
        config=config,
        document_key=key,
    )


def verify_callback_jwt(settings: Settings, *, header: str | None, body: dict[str, Any]) -> dict[str, Any]:
    """ONLYOFFICE ký callback bằng JWT (trong header hoặc trong thân); trả nội dung đã xác thực, sai thì từ chối."""
    token = header[7:] if header and header.lower().startswith("bearer ") else body.get("token")
    if not isinstance(token, str):
        raise PortalError(403, "EDITOR_LINK_INVALID", "portal.editor_link_invalid")
    try:
        payload = jwt_decode(token, _secret(settings))
    except InvalidTokenError as exc:
        raise PortalError(403, "EDITOR_LINK_INVALID", "portal.editor_link_invalid") from exc
    inner = payload.get("payload")
    return inner if isinstance(inner, dict) else payload


async def apply_saved_docx(
    session: AsyncSession,
    *,
    version_id: int,
    user_id: int,
    content: bytes,
    storage: StoragePort,
    settings: Settings,
) -> SaveFormat | None:
    """Ghi file .docx HR vừa lưu: đọc thành Markdown và giữ làm bản làm việc. Trả về định dạng file gốc HR đã chọn (để dựng file
    gốc sau đó), hoặc None nếu không ghi gì (không có lệnh lưu, bản nháp đã bị kích hoạt, hay chưa có thay đổi)."""
    version = await session.get(DocumentVersion, version_id)
    if version is None or version.status != VersionStatus.DRAFT:
        return None
    fmt = pending_save_format(version)
    if fmt is None:
        return None  # HR bấm Hủy (hoặc ONLYOFFICE gửi file lúc đóng): bỏ thay đổi
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        parsed = await asyncio.to_thread(parse_document, tmp_path)
    except ParseError as exc:
        raise PortalError(422, "VERSION_CONTENT_TOO_SHORT", "portal.version_content_too_short") from exc
    finally:
        tmp_path.unlink(missing_ok=True)
    try:
        storage_key = await storage.store(content, checksum=parsed.file_checksum, filename="tai-lieu.docx")
    except Exception as exc:
        raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc

    new_markdown, new_checksum, working = parsed.markdown, parsed.content_checksum, None
    patch_note: dict[str, Any] = {}
    previous = version.quality_report.get(WORKING_DOCX_KEY)
    if isinstance(previous, dict) and previous.get("baseline_key"):
        # Bản nháp từ PDF: vá đúng chỗ HR sửa vào Markdown gốc (đã chunk), giữ nguyên phần còn lại.
        try:
            baseline = (await _read_stored_file(str(previous["baseline_key"]), settings)).decode("utf-8")
        except (OSError, httpx.HTTPError):
            baseline = None
        if baseline is not None:
            result = await asyncio.to_thread(patch_markdown, version.markdown, baseline, parsed.markdown)
            patch_note = {"patched": result.ok, "groups": result.groups, "reason": result.reason}
            if result.ok:
                new_markdown = result.markdown
                new_checksum = checksum_of(new_markdown)
            working = {"baseline_key": await _store_text(storage, parsed.markdown)}
    markdown_changed = new_markdown != version.markdown
    version.parser = "markitdown"
    version.markdown = new_markdown
    version.content_checksum = new_checksum
    version.source = VersionSource.EDITED.value
    version.updated_by = user_id
    _, structure = analyze_structure(new_markdown, infer=False)
    report = {k: v for k, v in version.quality_report.items() if k != PENDING_SAVE_KEY}
    version.quality_report = {
        **report,
        "structure": structure.as_dict(),
        "has_embedded_images": parsed.has_embedded_images,
        WORKING_DOCX_KEY: {"storage_key": storage_key, "content_checksum": new_checksum, **(working or {})},
    }
    session.add(
        AuditLog(
            actor_id=user_id,
            action="SAVE_FROM_WORD_EDITOR",
            entity_type="document_version",
            entity_id=str(version.id),
            after={
                "document_id": version.document_id,
                "markdown_changed": markdown_changed,
                "original_format": fmt,
                **patch_note,
            },
        )
    )
    await session.commit()
    return fmt


async def finalize_original(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    storage: StoragePort,
    client: OnlyOfficeClient,
    *,
    version_id: int,
    user_id: int,
    fmt: SaveFormat,
) -> None:
    """Dựng và lưu "file gốc" theo lựa chọn của HR: PDF xuất từ bản Word vừa lưu, hoặc file Markdown. Chạy sau khi đã trả lời
    ONLYOFFICE (không chuyển đổi lồng trong lúc nó đang chờ). Lỗi chỉ ghi nhật ký: Markdown và bản làm việc đã lưu rồi."""
    try:
        async with session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None or version.status != VersionStatus.DRAFT:
                return
            if fmt == "markdown":
                content = version.markdown.encode("utf-8")
                filename, mime = f"{version.version_label}.md", "text/markdown"
            elif fmt == "docx":
                content = await stored_docx_bytes(version, settings)
                filename, mime = f"{version.version_label}.docx", DOCX_MIME
            else:
                token = make_link_token(settings, version_id=version.id, kind="docx", user_id=user_id)
                url = f"{settings.onlyoffice_backend_url.rstrip('/')}/api/v1/portal/editor-files/{token}"
                content = await client.convert(
                    source_url=url, filetype="docx", outputtype="pdf", key=f"f{document_key(version)}{int(time.time())}"
                )
                filename, mime = f"{version.version_label}.pdf", "application/pdf"
            checksum = hashlib.sha256(content).hexdigest()
            version.storage_key = await storage.store(content, checksum=checksum, filename=filename)
            version.file_checksum = checksum
            version.size_bytes = len(content)
            version.original_filename = filename
            version.mime_type = mime
            await session.commit()
    except Exception as exc:  # noqa: BLE001 - chạy nền: không để lỗi làm hỏng việc đã lưu
        logger.warning("editor_finalize_failed version=%s format=%s error=%s", version_id, fmt, type(exc).__name__)


PREVIEW_KEY = "preview_pdf"


async def preview_pdf_for(
    session: AsyncSession,
    version: DocumentVersion,
    settings: Settings,
    client: OnlyOfficeClient,
    storage: StoragePort,
    *,
    user_id: int,
) -> bytes:
    """PDF để xem "Bản gốc" của file Word: chuyển bằng ONLYOFFICE rồi lưu kèm, lần sau dùng lại (hợp lệ khi file gốc chưa đổi)."""
    cached = version.quality_report.get(PREVIEW_KEY)
    if isinstance(cached, dict) and cached.get("file_checksum") == version.file_checksum and cached.get("storage_key"):
        try:
            return await _read_stored_file(str(cached["storage_key"]), settings)
        except (OSError, httpx.HTTPError):
            pass  # mất bản lưu thì chuyển lại
    token = make_link_token(settings, version_id=version.id, kind="docx", user_id=user_id)
    url = f"{settings.onlyoffice_backend_url.rstrip('/')}/api/v1/portal/editor-files/{token}"
    content = await client.convert(
        source_url=url, filetype="docx", outputtype="pdf", key=f"v{document_key(version)}{int(time.time())}"
    )
    try:
        storage_key = await storage.store(content, checksum=hashlib.sha256(content).hexdigest(), filename="xem.pdf")
    except Exception as exc:
        raise PortalError(502, "STORAGE_FAILED", "portal.storage_failed") from exc
    version.quality_report = {
        **version.quality_report,
        PREVIEW_KEY: {"file_checksum": version.file_checksum, "storage_key": storage_key},
    }
    await session.commit()
    return content


async def load_version(session: AsyncSession, *, version_id: int, document_id: int | None = None) -> DocumentVersion:
    query = select(DocumentVersion).where(DocumentVersion.id == version_id)
    if document_id is not None:
        query = query.where(DocumentVersion.document_id == document_id)
    version = await session.scalar(query)
    if version is None:
        raise PortalError(404, "DOCUMENT_VERSION_NOT_FOUND", "portal.document_version_not_found")
    return version
