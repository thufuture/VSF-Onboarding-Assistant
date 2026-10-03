"""Công cụ lộ trình tất định của Viga (mục 15.4, 17.6): chỉ ĐỌC, chỉ trên lộ trình của chính người hỏi, không LLM, không bịa.

Mỗi công cụ trả `ToolReply` đúng hình dạng giao diện nhân viên đã dùng (response_type, message, blocking_tasks,
suggested_actions, sources). Viga **không có công cụ ghi** vào trạng thái việc: không tự đánh dấu hoàn thành, không duyệt.

Câu trả lời đi kèm `message_key` + `params` để giao diện dịch theo ngôn ngữ đang chọn; `message` là bản tiếng Việt dự phòng
(dùng cho client không biết khóa và cho test).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from src.services.viga.snapshot import JourneySnapshot, SnapshotDay, SnapshotTask

ResponseType = Literal[
    "NEXT_STEP",
    "PREREQUISITE_REQUIRED",
    "DAY_PLAN",
    "INFO",
    "NOT_IN_JOURNEY",
    "CLARIFY",
    "NO_BASIS",
    "OUT_OF_SCOPE",
    "ERROR",
]

TOOL_NAMES = (
    "get_next_tasks",
    "get_day_plan",
    "explain_lock",
    "get_task_detail",
    "get_progress",
    "search_documents",
)
TASK_TOOLS = ("explain_lock", "get_task_detail")
MAX_LISTED = 6
DETAIL_MAX_CHARS = 700

_TEMPLATES = {
    "nextStep": "Bạn có thể làm ngay việc “{title}”.",
    "allDone": "Bạn đã hoàn thành toàn bộ việc trong lộ trình.",
    "taskDone": "Bạn đã hoàn thành việc “{title}”.",
    "locked": "Bạn chưa làm được “{title}” vì cần hoàn thành “{blocker}” trước.",
    "taskReady": "Việc “{title}” đang mở, bạn làm được ngay.",
    "dayPlan": "{day}: có {ready} việc làm được ngay trong tổng {total} việc.",
    "dayPlanEmpty": "{day}: hiện chưa có việc nào làm được ngay.",
    "dayNotFound": "Mình không thấy ngày đó trong lộ trình của bạn.",
    "notInJourney": "Việc này không có trong lộ trình của bạn.",
    "progress": "Bạn đã hoàn thành {done}/{total} việc ({percent}%).",
    "taskDetail": "Hướng dẫn “{title}”:\n{detail}",
    "clarifyTask": "Bạn đang nói về việc nào?",
    "noJourney": "Bạn chưa có lộ trình onboarding nên mình chưa tra được việc cần làm.",
    "noTaskNow": "Hiện chưa có việc nào làm được ngay.",
    "noBasis": "Mình chưa có căn cứ trong tài liệu để trả lời câu này.",
    "outOfScope": "Thông tin này không có trong tài liệu chung, bạn hỏi HR phụ trách nhé.",
    "assistantUnavailable": "Viga tạm thời chưa trả lời được, bạn thử lại sau nhé.",
    "smalltalk": "Mình là Viga, chuyên dẫn đường lộ trình onboarding và tra tài liệu HR đã đăng. Bạn hỏi mình về việc cần làm hoặc nội quy nhé.",
}


def render(key: str, **params: Any) -> str:
    return _TEMPLATES[key].format(**params)


@dataclass(frozen=True)
class BlockingTask:
    task_id: int
    title: str
    state: str  # done | ready | locked


@dataclass(frozen=True)
class SuggestedAction:
    type: Literal["OPEN_TASK", "OPEN_DAY"]
    title: str
    task_id: int | None = None
    stage_id: int | None = None


@dataclass(frozen=True)
class SourceRef:
    kind: Literal["TASK", "DAY"]
    title: str


@dataclass(frozen=True)
class ToolReply:
    response_type: ResponseType
    message_key: str
    params: dict[str, str | int]
    message: str
    blocking_tasks: list[BlockingTask] = field(default_factory=list)
    actions: list[SuggestedAction] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    assumed_title: str | None = None  # "Mình đang hiểu bạn nói về việc ..." khi phải suy ra việc


def reply(
    response_type: ResponseType,
    key: str,
    *,
    blocking: list[BlockingTask] | None = None,
    actions: list[SuggestedAction] | None = None,
    sources: list[SourceRef] | None = None,
    **params: str | int,
) -> ToolReply:
    return ToolReply(
        response_type=response_type,
        message_key=key,
        params=dict(params),
        message=render(key, **params),
        blocking_tasks=blocking or [],
        actions=actions or [],
        sources=sources or [],
    )


def strip_accents(text: str) -> str:
    """Chữ thường, bỏ dấu tiếng Việt để so khớp từ khóa (giữ bản có dấu cho hiển thị)."""
    decomposed = unicodedata.normalize("NFD", text.lower().replace("đ", "d"))
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


_STOP_WORDS = {
    "task", "viec", "nay", "kia", "lam", "the", "nao", "sao", "chua", "duoc", "cho", "minh", "hoi", "toi", "khong",
    "va", "cua", "la", "co", "bi", "khoa", "huong", "dan", "nhu", "gi", "den", "ve", "mot", "cac", "nhung",
    "de", "da", "se", "ma", "cu", "khi", "neu", "hay", "roi", "ra", "vao", "tai", "trong", "voi", "can", "phai", "bao", "nhieu",
}  # fmt: skip


def _words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", strip_accents(text)) if len(w) >= 2 and w not in _STOP_WORDS]


def match_tasks_by_name(snapshot: JourneySnapshot, question: str) -> list[SnapshotTask]:
    """Việc khớp tên nhất trong lộ trình của người hỏi (cùng điểm cao nhất thì trả cả nhóm hòa).

    Cần khớp tối thiểu 2 từ tên việc (hoặc toàn bộ từ nếu tên việc ngắn hơn) để không trả lời bừa.
    """
    asked = set(_words(question))
    if not asked:
        return []
    scored: list[tuple[int, SnapshotTask]] = []
    for task in snapshot.tasks:
        title_words = set(_words(task.title))
        if not title_words:
            continue
        score = len(asked & title_words)
        if score >= min(2, len(title_words)):
            scored.append((score, task))
    if not scored:
        return []
    top = max(score for score, _ in scored)
    return [task for score, task in scored if score == top]


_ORDINAL_RE = re.compile(r"\b(?:viec|task|buoc)\s*(?:so\s*)?0*(\d{1,2})\b")


def task_by_ordinal(snapshot: JourneySnapshot, question: str) -> SnapshotTask | None:
    """ "việc số 3", "task 03": thứ tự trong ngày đang làm (nhờ số thứ tự đã hiện trên roadmap)."""
    match = _ORDINAL_RE.search(strip_accents(question))
    day = snapshot.current_day
    if match is None or day is None:
        return None
    index = int(match.group(1)) - 1
    return day.tasks[index] if 0 <= index < len(day.tasks) else None


@dataclass(frozen=True)
class Resolution:
    task: SnapshotTask | None
    candidates: list[SnapshotTask]  # nhiều việc khớp ngang nhau: hỏi lại, không tự chọn bừa
    assumed: bool  # True khi phải suy bằng "việc làm được ngay đầu tiên" và cần nói rõ giả định


def resolve_task(snapshot: JourneySnapshot, question: str, explicit_id: int | None, now: datetime) -> Resolution:
    """Xác định "việc nào" theo thứ tự đã chốt (mục 15.3d, 15.3e).

    1. Mã việc LLM/giao diện nêu (đã kiểm thuộc lộ trình) -> 2. nêu tên hoặc số thứ tự trong câu hỏi ->
    3. việc vừa mở trong 30 phút -> 4. việc làm được ngay đầu tiên (nói rõ giả định) -> không có thì hỏi lại.
    """
    if explicit_id is not None:
        task = snapshot.get(explicit_id)
        return Resolution(task, [], False)
    ordinal = task_by_ordinal(snapshot, question)
    if ordinal is not None:
        return Resolution(ordinal, [], False)
    named = match_tasks_by_name(snapshot, question)
    if len(named) == 1:
        return Resolution(named[0], [], False)
    if len(named) > 1:
        return Resolution(None, named[:3], False)
    opened = snapshot.last_opened(now)
    if opened is not None:
        return Resolution(opened, [], False)
    ready = snapshot.ready_tasks()
    if ready:
        return Resolution(ready[0], [], True)
    return Resolution(None, [], False)


def _open_task(task: SnapshotTask) -> SuggestedAction:
    return SuggestedAction("OPEN_TASK", task.title, task_id=task.id)


def _open_day(day: SnapshotDay) -> SuggestedAction:
    return SuggestedAction("OPEN_DAY", day.title, stage_id=day.stage_id)


def _blocking(task: SnapshotTask) -> BlockingTask:
    return BlockingTask(task.id, task.title, task.state)


def get_next_tasks(snapshot: JourneySnapshot) -> ToolReply:
    ready = snapshot.ready_tasks()
    if not ready:
        key = "allDone" if snapshot.total and snapshot.done == snapshot.total else "noTaskNow"
        day = snapshot.current_day
        return reply("INFO", key, actions=[_open_day(day)] if day else [])
    first = ready[0]
    day = snapshot.current_day
    return reply(
        "NEXT_STEP",
        "nextStep",
        title=first.title,
        blocking=[_blocking(task) for task in ready[:MAX_LISTED]],
        actions=[_open_task(first), *([_open_day(day)] if day else [])],
        sources=[SourceRef("TASK", first.title)],
    )


def _pick_day(snapshot: JourneySnapshot, day: str | int | None) -> SnapshotDay | None:
    days = snapshot.days
    if not days:
        return None
    current = snapshot.current_day
    if day is None or day == "today":
        return current
    if day == "tomorrow":
        index = days.index(current) + 1 if current in days else len(days)
        return days[index] if index < len(days) else None
    if isinstance(day, int) and 1 <= day <= len(days):
        return days[day - 1]
    return None


def get_day_plan(snapshot: JourneySnapshot, day: str | int | None = None) -> ToolReply:
    chosen = _pick_day(snapshot, day)
    if chosen is None:
        return reply("INFO", "dayNotFound")
    ready = chosen.ready
    first = ready[0] if ready else None
    key = "dayPlan" if ready else "dayPlanEmpty"
    return reply(
        "DAY_PLAN",
        key,
        day=chosen.title,
        ready=len(ready),
        total=chosen.total,
        blocking=[_blocking(task) for task in chosen.tasks[:MAX_LISTED]],
        actions=[_open_day(chosen), *([_open_task(first)] if first else [])],
        sources=[SourceRef("DAY", chosen.title)],
    )


def explain_lock(snapshot: JourneySnapshot, task: SnapshotTask | None) -> ToolReply:
    if task is None:
        return reply("NOT_IN_JOURNEY", "notInJourney")
    source = [SourceRef("TASK", task.title)]
    if task.state == "done":
        return reply("INFO", "taskDone", title=task.title, actions=[_open_task(task)], sources=source)
    if task.state == "ready":
        return reply("INFO", "taskReady", title=task.title, actions=[_open_task(task)], sources=source)
    blockers = [b for b in (snapshot.get(pid) for pid in task.prerequisite_ids) if b is not None and b.state != "done"]
    first = blockers[0] if blockers else None
    return reply(
        "PREREQUISITE_REQUIRED",
        "locked",
        title=task.title,
        blocker=first.title if first else "",
        blocking=[_blocking(b) for b in blockers],
        actions=[_open_task(first)] if first else [_open_task(task)],
        sources=source,
    )


def get_task_detail(task: SnapshotTask | None) -> ToolReply:
    if task is None:
        return reply("NOT_IN_JOURNEY", "notInJourney")
    detail = task.body_markdown.strip()
    if len(detail) > DETAIL_MAX_CHARS:
        detail = detail[:DETAIL_MAX_CHARS].rstrip() + "…"
    return reply(
        "INFO",
        "taskDetail",
        title=task.title,
        detail=detail,
        actions=[_open_task(task)],
        sources=[SourceRef("TASK", task.title)],
    )


def get_progress(snapshot: JourneySnapshot) -> ToolReply:
    day = snapshot.current_day
    return reply(
        "INFO",
        "progress",
        done=snapshot.done,
        total=snapshot.total,
        percent=snapshot.percent,
        actions=[_open_day(day)] if day else [],
    )


def clarify(candidates: list[SnapshotTask], text: str | None = None) -> ToolReply:
    """Một câu hỏi lại kèm tối đa 3 việc để bấm; không tự chọn bừa khi mơ hồ."""
    chosen = candidates[:3]
    base = reply("CLARIFY", "clarifyTask", actions=[_open_task(task) for task in chosen])
    if text:
        return ToolReply(
            base.response_type, "clarifyCustom", {}, text.strip(), base.blocking_tasks, base.actions, base.sources
        )
    return base


def no_journey() -> ToolReply:
    return reply("INFO", "noJourney")


def run_task_tool(
    name: str, snapshot: JourneySnapshot, question: str, explicit_id: int | None, now: datetime
) -> ToolReply:
    """Công cụ cần biết "việc nào": xác định theo thứ tự đã chốt, nói rõ giả định khi phải suy ra, hỏi lại khi mơ hồ."""
    resolution = resolve_task(snapshot, question, explicit_id, now)
    if resolution.candidates:
        return clarify(resolution.candidates)
    if resolution.task is None:
        if explicit_id is not None:
            return explain_lock(snapshot, None)
        return clarify(snapshot.ready_tasks()[:3]) if snapshot.ready_tasks() else reply("INFO", "noTaskNow")
    result = explain_lock(snapshot, resolution.task) if name == "explain_lock" else get_task_detail(resolution.task)
    if resolution.assumed:
        return ToolReply(
            result.response_type,
            result.message_key,
            result.params,
            result.message,
            result.blocking_tasks,
            result.actions,
            result.sources,
            assumed_title=resolution.task.title,
        )
    return result


def run_tool(
    name: str,
    snapshot: JourneySnapshot,
    *,
    question: str,
    args: dict[str, Any],
    now: datetime,
) -> ToolReply:
    if name == "get_next_tasks":
        return get_next_tasks(snapshot)
    if name == "get_day_plan":
        return get_day_plan(snapshot, args.get("day"))
    if name == "get_progress":
        return get_progress(snapshot)
    if name in TASK_TOOLS:
        task_id = args.get("task_id")
        return run_task_tool(name, snapshot, question, task_id if isinstance(task_id, int) else None, now)
    raise ValueError(f"công cụ không hợp lệ: {name}")
