"""Bổ sung câu trả lời cho một câu Viga chưa trả lời được: HR viết đáp án ngay trên trang Phản hồi Viga.

Mỗi phòng ban có một tài liệu "Hỏi đáp bổ sung" (khóa `qa-supplement-team-<id>`; ADMIN không thuộc phòng ban dùng bản dùng chung).
Mỗi lần thêm là một mục Hỏi đáp (tiêu đề = câu hỏi, nội dung = câu trả lời, đầu mối nếu có) vào bản đang áp dụng, tạo thành bản nháp
mới rồi xếp việc nền kích hoạt (chunk + embedding) như mọi tài liệu khác. Chọn dạng "câu hỏi làm tiêu đề" vì đo thực tế cho thấy
Viga trả lời tốt nhất với kiểu tài liệu này (báo cáo kiểm tra 02/10).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.document import Document
from src.model.document_version import DocumentVersion
from src.model.enums import VersionStatus
from src.model.user import User
from src.services.ingest.storage import StoragePort
from src.services.portal import document_version_service
from src.services.portal.errors import PortalError

SUPPLEMENT_TITLE = "Hỏi đáp bổ sung"
SUPPLEMENT_CATEGORY = "tai-lieu-khac"
QUESTION_MAX_CHARS = 300
ANSWER_MAX_CHARS = 3000
CONTACT_MAX_CHARS = 200

_INTRO = (
    "Tài liệu này do HR bổ sung từ những câu hỏi thực tế của nhân sự mới mà các tài liệu khác chưa trả lời được. "
    "Mỗi mục bên dưới là một câu hỏi kèm câu trả lời chính thức và đầu mối liên hệ nếu có."
)


@dataclass(frozen=True)
class SupplementResult:
    document_id: int
    version_id: int
    version_label: str
    job_id: int


def source_key_for(team_id: int | None) -> str:
    return f"qa-supplement-team-{team_id}" if team_id is not None else "qa-supplement-shared"


def render_entry(question: str, answer: str, contact: str | None) -> str:
    lines = [f"## {question}", "", answer.strip()]
    if contact:
        lines += ["", f"Đầu mối: {contact}"]
    return "\n".join(lines)


def _clean_line(text: str, limit: int) -> str:
    return " ".join(text.split())[:limit]


async def add_answer(
    session: AsyncSession,
    *,
    user: User,
    team_id: int | None,
    question: str,
    answer: str,
    contact: str | None,
    storage: StoragePort,
    today: date,
) -> SupplementResult:
    clean_question = _clean_line(question, QUESTION_MAX_CHARS)
    clean_answer = "\n".join(line.rstrip() for line in answer.strip().splitlines())[:ANSWER_MAX_CHARS]
    clean_contact = _clean_line(contact or "", CONTACT_MAX_CHARS) or None
    if not clean_question or len(clean_answer.strip()) < 5:
        raise PortalError(422, "SUPPLEMENT_ANSWER_REQUIRED", "portal.supplement_answer_required")

    source_key = source_key_for(team_id)
    document = await session.scalar(select(Document).where(Document.source_key == source_key))
    base = f"# {SUPPLEMENT_TITLE}\n\n{_INTRO}"
    revision = 1
    if document is not None:
        revision = (
            int(
                await session.scalar(
                    select(func.coalesce(func.max(DocumentVersion.revision_no), 0)).where(
                        DocumentVersion.document_id == document.id
                    )
                )
                or 0
            )
            + 1
        )
        current = await session.scalar(
            select(DocumentVersion.markdown)
            .where(DocumentVersion.document_id == document.id, DocumentVersion.status == VersionStatus.ACTIVE.value)
            .order_by(DocumentVersion.revision_no.desc())
            .limit(1)
        )
        if current:
            base = current.rstrip()
    markdown = f"{base}\n\n{render_entry(clean_question, clean_answer, clean_contact)}\n"

    label = f"Bổ sung {revision}"
    draft = await document_version_service.create_draft_from_upload(
        session,
        content=markdown.encode("utf-8"),
        filename="hoi-dap-bo-sung.md",
        actor=user,
        storage=storage,
        version_label=label,
        effective_from=None,
        document_id=document.id if document is not None else None,
        title=SUPPLEMENT_TITLE,
        category_slug=SUPPLEMENT_CATEGORY,
        source_key=source_key,
    )
    job = await document_version_service.activate_version(
        session,
        document_id=draft.document_id,
        version_id=draft.version_id,
        actor=user,
        effective_from=None,
        today=today,
    )
    return SupplementResult(
        document_id=draft.document_id, version_id=draft.version_id, version_label=label, job_id=job.id
    )
