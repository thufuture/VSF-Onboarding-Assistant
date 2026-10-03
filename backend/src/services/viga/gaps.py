"""Câu hỏi Viga chưa trả lời được ("content gap", mục 17.5): để HR bổ sung tài liệu.

HR chỉ thấy câu hỏi của **phòng ban mình** và **ẩn danh** (không có tên người hỏi): hội thoại cá nhân không đọc được, chỉ nội
dung câu chưa trả lời được mới đi tới HR (quyết định 8, mục 0.1). Câu giống nhau (so khớp không dấu, không phân biệt hoa thường)
được gom lại và đếm số lần hỏi.

Hai loại: `NO_BASIS` (cả câu không có căn cứ) và `PARTIAL` (đã trả lời được một phần, phần còn lại tài liệu chưa quy định).
Sau khi HR bổ sung tài liệu, `recheck_group` hỏi lại đúng câu đó; chỉ khi Viga trả lời được mới tự đánh dấu đã xử lý.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.content_gap import ContentGap
from src.model.document import Document
from src.model.document_version import DocumentVersion
from src.model.enums import GapKind
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.chat.pipeline import run_document_qa
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.portal.errors import PortalError
from src.services.viga.guard import normalize_question

QUESTION_MAX_CHARS = 500
EXCERPT_MAX_CHARS = 600
DUPLICATE_WINDOW = timedelta(minutes=10)


async def team_of(session: AsyncSession, user_id: int) -> int | None:
    value = await session.scalar(
        select(TeamMember.team_id).where(TeamMember.user_id == user_id).order_by(TeamMember.team_id).limit(1)
    )
    return int(value) if value is not None else None


async def log_content_gap(
    session: AsyncSession,
    user: User,
    question: str,
    *,
    related_employee_task_id: int | None = None,
    kind: GapKind = GapKind.NO_BASIS,
    answer_excerpt: str | None = None,
) -> bool:
    """Ghi một câu hỏi chưa trả lời được. Trả `False` nếu bỏ qua (chưa có phòng ban, hoặc đã ghi y hệt trong 10 phút)."""
    team_id = await team_of(session, user.id)
    text = " ".join(question.split())[:QUESTION_MAX_CHARS]
    if team_id is None or not text:
        return False
    since = datetime.now(UTC) - DUPLICATE_WINDOW
    recent = await session.scalars(
        select(ContentGap.question_text).where(ContentGap.asked_by_user_id == user.id, ContentGap.created_at >= since)
    )
    wanted = normalize_question(text)
    if any(normalize_question(existing) == wanted for existing in recent.all()):
        return False
    excerpt = " ".join(answer_excerpt.split())[:EXCERPT_MAX_CHARS] if answer_excerpt else None
    session.add(
        ContentGap(
            team_id=team_id,
            asked_by_user_id=user.id,
            related_employee_task_id=related_employee_task_id,
            question_text=text,
            kind=kind.value,
            answer_excerpt=excerpt,
        )
    )
    await session.commit()
    return True


@dataclass(frozen=True)
class GapGroup:
    id: int  # mã một dòng đại diện của nhóm (dùng để đánh dấu đã xử lý / kiểm lại cả nhóm)
    question_text: str
    occurrences: int
    first_asked_at: datetime
    last_asked_at: datetime
    resolved: bool
    kind: str  # NO_BASIS nếu còn lần nào không có căn cứ hoàn toàn, ngược lại PARTIAL
    answer_excerpt: str | None  # phần Viga đã trả lời được (loại PARTIAL)
    resolved_document_title: str | None  # tài liệu HR đã bổ sung để đóng câu này


async def list_gap_groups(session: AsyncSession, *, team_id: int | None, include_resolved: bool) -> list[GapGroup]:
    """Các nhóm câu hỏi giống nhau trong phạm vi `team_id` (None = mọi phòng ban, dành cho ADMIN), ẩn danh."""
    query = select(ContentGap).order_by(ContentGap.created_at.desc())
    if team_id is not None:
        query = query.where(ContentGap.team_id == team_id)
    rows = (await session.scalars(query)).all()
    groups: dict[str, list[ContentGap]] = {}
    for row in rows:
        groups.setdefault(normalize_question(row.question_text), []).append(row)

    version_ids = {row.resolved_by_version_id for row in rows if row.resolved_by_version_id is not None}
    titles: dict[int, str] = {}
    if version_ids:
        title_rows = await session.execute(
            select(DocumentVersion.id, Document.title)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(DocumentVersion.id.in_(version_ids))
        )
        titles = {version_id: title for version_id, title in title_rows.all()}

    result: list[GapGroup] = []
    for items in groups.values():
        unresolved = [item for item in items if item.resolved_at is None]
        resolved = not unresolved
        if resolved and not include_resolved:
            continue
        latest = items[0]
        open_items = unresolved or items
        kind = (
            GapKind.NO_BASIS.value
            if any(i.kind == GapKind.NO_BASIS.value for i in open_items)
            else GapKind.PARTIAL.value
        )
        excerpt = next((i.answer_excerpt for i in open_items if i.answer_excerpt), None)
        resolved_by = next((i.resolved_by_version_id for i in items if i.resolved_by_version_id is not None), None)
        result.append(
            GapGroup(
                id=open_items[0].id,
                question_text=latest.question_text,
                occurrences=len(items),
                first_asked_at=min(item.created_at for item in items),
                last_asked_at=max(item.created_at for item in items),
                resolved=resolved,
                kind=kind,
                answer_excerpt=excerpt,
                resolved_document_title=titles.get(resolved_by) if resolved_by is not None else None,
            )
        )
    return sorted(result, key=lambda g: (g.resolved, -g.occurrences, -g.last_asked_at.timestamp()))


async def scoped_gap(session: AsyncSession, gap_id: int, team_id: int | None) -> ContentGap:
    gap = await session.get(ContentGap, gap_id)
    if gap is None or (team_id is not None and gap.team_id != team_id):
        raise PortalError(404, "CONTENT_GAP_NOT_FOUND", "portal.content_gap_not_found")
    return gap


async def resolve_group(
    session: AsyncSession, *, gap_id: int, team_id: int | None, resolved_by_version_id: int | None = None
) -> int:
    """Đánh dấu đã xử lý cả nhóm câu hỏi giống `gap_id` (cùng phạm vi phòng ban). Trả số dòng đã đóng."""
    gap = await scoped_gap(session, gap_id, team_id)
    wanted = normalize_question(gap.question_text)
    candidates = (
        await session.scalars(
            select(ContentGap).where(ContentGap.team_id == gap.team_id, ContentGap.resolved_at.is_(None))
        )
    ).all()
    ids = [item.id for item in candidates if normalize_question(item.question_text) == wanted]
    if ids:
        await session.execute(
            update(ContentGap)
            .where(ContentGap.id.in_(ids))
            .values(resolved_at=func.now(), resolved_by_version_id=resolved_by_version_id)
        )
    await session.commit()
    return len(ids)


@dataclass(frozen=True)
class RecheckResult:
    answered: bool
    message: str | None
    document_title: str | None
    section_heading: str | None
    quote: str | None
    closed: int  # số dòng đã tự đóng (0 nếu chưa trả lời được)


async def recheck_group(
    session: AsyncSession,
    *,
    gap_id: int,
    team_id: int | None,
    session_factory: async_sessionmaker[AsyncSession],
    llm: ChatCompletionPort,
    embedding: EmbeddingPort,
    tracer: LangfuseTracer,
    today: date,
) -> RecheckResult:
    """Hỏi lại đúng câu hỏi bằng tài liệu hiện tại. Trả lời được thì đóng cả nhóm và ghi tài liệu đã bổ sung."""
    gap = await scoped_gap(session, gap_id, team_id)
    result = await run_document_qa(
        gap.question_text,
        llm=llm,
        embedding=embedding,
        session_factory=session_factory,
        tracer=tracer,
        as_of=today,
        history=[],
    )
    answers = [c for c in result.claims if c.response_type == "ANSWER" and c.text]
    if not answers:
        return RecheckResult(False, None, None, None, None, 0)
    first = answers[0]
    section = result.section_by_chunk.get(first.chunk_id) if first.chunk_id is not None else None
    texts = list(dict.fromkeys(c.text for c in answers if c.text))
    closed = await resolve_group(
        session, gap_id=gap_id, team_id=team_id, resolved_by_version_id=section.version_id if section else None
    )
    return RecheckResult(
        answered=True,
        message=" ".join(texts),
        document_title=section.document_title if section else None,
        section_heading=section.heading if section else None,
        quote=first.quote,
        closed=closed,
    )
