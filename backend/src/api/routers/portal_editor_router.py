"""`/api/v1/portal` — soạn thảo bản nháp bằng trình soạn thảo kiểu Word (ONLYOFFICE). Tắt mặc định, xem `word_editor.py`.

Hai đường dẫn `editor-files/{token}` và `editor-callback/{token}` do **máy chủ ONLYOFFICE** gọi (không có cookie đăng nhập), nên được
bảo vệ bằng mã ký ngắn hạn gắn với một phiên bản và một người dùng; callback còn phải có JWT hợp lệ của ONLYOFFICE.
"""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Request, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db, get_storage_port, require_role
from src.config import Settings, get_settings
from src.model.enums import UserRole, VersionStatus
from src.model.user import User
from src.services.ingest.storage import StoragePort
from src.services.portal import word_editor
from src.services.portal.errors import PortalError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/portal", tags=["portal-editor"])

StaffUser = Annotated[User, Depends(require_role(UserRole.HR, UserRole.ADMIN))]
Db = Annotated[AsyncSession, Depends(get_db)]
AppSettings = Annotated[Settings, Depends(get_settings)]


def get_onlyoffice_client(settings: AppSettings) -> word_editor.OnlyOfficeClient:
    return word_editor.OnlyOfficeClient(settings)


OnlyOffice = Annotated[word_editor.OnlyOfficeClient, Depends(get_onlyoffice_client)]


class CapabilitiesResponseDTO(BaseModel):
    word_editor: bool


class EditorSessionResponseDTO(BaseModel):
    api_js_url: str
    config: dict[str, Any]
    document_key: str


class EditorSaveRequestDTO(BaseModel):
    document_key: str
    # Định dạng "file gốc" HR chọn ở hộp Lưu: PDF xuất từ bản Word, hoặc file Markdown.
    format: Literal["docx", "pdf", "markdown"]


class EditorSaveResponseDTO(BaseModel):
    ok: bool
    # False: trình soạn thảo báo không có thay đổi nào để lưu.
    changed: bool = True


@router.get("/capabilities", response_model=CapabilitiesResponseDTO)
async def capabilities(_user: StaffUser, settings: AppSettings) -> CapabilitiesResponseDTO:
    try:
        word_editor.require_enabled(settings)
    except PortalError:
        return CapabilitiesResponseDTO(word_editor=False)
    return CapabilitiesResponseDTO(word_editor=True)


@router.post("/documents/{document_id}/versions/{version_id}/editor-session", response_model=EditorSessionResponseDTO)
async def open_editor_session(
    document_id: int,
    version_id: int,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
    onlyoffice: OnlyOffice,
    storage: Annotated[StoragePort, Depends(get_storage_port)],
) -> EditorSessionResponseDTO:
    """Cấu hình để giao diện mở trình soạn thảo Word cho một **bản nháp** (bản đã kích hoạt không sửa tại chỗ)."""
    word_editor.require_enabled(settings)
    version = await word_editor.load_version(db, version_id=version_id, document_id=document_id)
    if version.status != VersionStatus.DRAFT:
        raise PortalError(409, "VERSION_NOT_EDITABLE", "portal.version_not_editable")
    await word_editor.ensure_docx_file(db, version, settings, onlyoffice, storage, user_id=user.id)
    session = word_editor.build_session(version, settings, user)
    return EditorSessionResponseDTO(
        api_js_url=session.api_js_url, config=session.config, document_key=session.document_key
    )


@router.post("/documents/{document_id}/versions/{version_id}/editor-session/save", response_model=EditorSaveResponseDTO)
async def save_editor_session(
    document_id: int,
    version_id: int,
    body: EditorSaveRequestDTO,
    _user: StaffUser,
    db: Db,
    settings: AppSettings,
    onlyoffice: OnlyOffice,
) -> EditorSaveResponseDTO:
    """Yêu cầu trình soạn thảo lưu ngay (không cần đóng). File về qua callback; giao diện hỏi lại bản nháp để thấy nội dung mới."""
    word_editor.require_enabled(settings)
    version = await word_editor.load_version(db, version_id=version_id, document_id=document_id)
    if version.status != VersionStatus.DRAFT:
        raise PortalError(409, "VERSION_NOT_EDITABLE", "portal.version_not_editable")
    # Đánh dấu "HR đã bấm Lưu và chọn định dạng": chỉ khi có dấu này, file ONLYOFFICE gửi về mới được ghi (Hủy thì bỏ).
    await word_editor.set_pending_save(db, version, body.format)
    result = await onlyoffice.command("forcesave", body.document_key)
    code = result.get("error")
    if code == 4:  # không có thay đổi nào: không có file nào sẽ về, bỏ dấu để lần sau không ghi nhầm
        await word_editor.set_pending_save(db, version, None)
        return EditorSaveResponseDTO(ok=True, changed=False)
    if code != 0:
        await word_editor.set_pending_save(db, version, None)
        return EditorSaveResponseDTO(ok=False)
    return EditorSaveResponseDTO(ok=True, changed=True)


@router.get("/documents/{document_id}/versions/{version_id}/export")
async def export_version(
    document_id: int,
    version_id: int,
    user: StaffUser,
    db: Db,
    settings: AppSettings,
    onlyoffice: OnlyOffice,
    format: Literal["docx", "pdf"] = "docx",
) -> Response:
    """Xuất bản nháp (hoặc bất kỳ phiên bản nào) thành Word hoặc PDF để tải về. Không đổi dữ liệu."""
    word_editor.require_enabled(settings)
    version = await word_editor.load_version(db, version_id=version_id, document_id=document_id)
    if format == "docx":
        content = await word_editor.docx_bytes_for(version, settings, onlyoffice, user_id=user.id)
        media = word_editor.DOCX_MIME
    else:
        # File Word còn khớp thì chuyển nó sang PDF; chưa có thì chuyển thẳng từ HTML dựng từ Markdown (không cần file trung gian).
        use_docx = word_editor.stored_docx_is_current(version)
        kind = "docx" if use_docx else "html"
        token = word_editor.make_link_token(settings, version_id=version.id, kind=kind, user_id=user.id)
        url = f"{settings.onlyoffice_backend_url.rstrip('/')}/api/v1/portal/editor-files/{token}"
        content = await onlyoffice.convert(
            source_url=url, filetype=kind, outputtype="pdf", key=f"p{word_editor.document_key(version)}"
        )
        media = "application/pdf"
    filename = f"{version.version_label}.{format}".replace('"', "")
    return Response(content, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/editor-files/{token}")
async def editor_file(token: str, db: Db, settings: AppSettings, onlyoffice: OnlyOffice) -> Response:
    """Máy chủ ONLYOFFICE lấy nội dung để mở hoặc chuyển đổi: `html` (dựng từ Markdown) hoặc `docx` (file đang lưu hoặc dựng mới)."""
    word_editor.require_enabled(settings)
    try:
        version_id, user_id = word_editor.read_link_token(settings, token, kind="docx")
        kind = "docx"
    except PortalError:
        version_id, user_id = word_editor.read_link_token(settings, token, kind="html")
        kind = "html"
    version = await word_editor.load_version(db, version_id=version_id)
    if kind == "html":
        return Response(word_editor.markdown_to_html(version.markdown), media_type="text/html; charset=utf-8")
    return Response(await word_editor.stored_docx_bytes(version, settings), media_type=word_editor.DOCX_MIME)


@router.post("/editor-callback/{token}")
async def editor_callback(
    token: str,
    request: Request,
    background: BackgroundTasks,
    db: Db,
    settings: AppSettings,
    storage: Annotated[StoragePort, Depends(get_storage_port)],
    onlyoffice: OnlyOffice,
    authorization: Annotated[str | None, Header()] = None,
) -> dict[str, int]:
    """ONLYOFFICE báo trạng thái lưu. Trả `{"error": 0}` khi đã xử lý; lỗi khác 0 thì ONLYOFFICE thử gửi lại."""
    word_editor.require_enabled(settings)
    version_id, user_id = word_editor.read_link_token(settings, token, kind="callback")
    body = await request.json()
    if not isinstance(body, dict):
        raise PortalError(400, "EDITOR_CALLBACK_BODY", "portal.editor_callback_body")
    payload = word_editor.verify_callback_jwt(settings, header=authorization, body=body)
    status = int(payload.get("status", 0))
    url = payload.get("url")
    if status not in word_editor.SAVE_STATUSES or not isinstance(url, str):
        return {"error": 0}  # đang mở, đóng không thay đổi, v.v.: không có file mới
    try:
        # Chỉ ghi khi HR đã bấm Lưu (có dấu chờ lưu); đóng bằng Hủy thì ONLYOFFICE vẫn gửi file nhưng ta bỏ qua.
        version = await word_editor.load_version(db, version_id=version_id)
        if word_editor.pending_save_format(version) is None:
            return {"error": 0}
        content = await onlyoffice.download(url)
        fmt = await word_editor.apply_saved_docx(
            db, version_id=version_id, user_id=user_id, content=content, storage=storage, settings=settings
        )
    except PortalError as exc:
        logger.warning("editor_callback_failed version=%s code=%s", version_id, exc.code)
        return {"error": 1}
    if fmt is not None:
        background.add_task(
            word_editor.finalize_original,
            request.app.state.session_factory,
            settings,
            storage,
            onlyoffice,
            version_id=version_id,
            user_id=user_id,
            fmt=fmt,
        )
    return {"error": 0}
