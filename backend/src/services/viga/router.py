"""LLM định tuyến của Viga (mục 17): MỘT lần gọi chọn công cụ trong danh sách đóng và điền tham số; code kiểm lại mọi thứ.

LLM **không bao giờ** là nguồn của câu trả lời cuối: nó chỉ chọn nhãn công cụ + tham số. Câu trả lời đến từ công cụ tất định
(lộ trình thật) hoặc từ pipeline tài liệu đã kiểm chứng nguyên văn. Mọi đầu ra của LLM bị kiểm bằng code:

- tên công cụ phải nằm trong danh sách đóng; tham số đúng kiểu;
- `task_id` phải thuộc lộ trình CỦA NGƯỜI HỎI (không tin mã do LLM đưa ra: bịa hoặc của người khác đều bị chặn);
- `confidence` dưới ngưỡng thì không dùng công cụ, rơi về hỏi đáp tài liệu.

Dữ liệu gửi cho LLM: câu hỏi, vài lượt gần nhất, và `JourneySnapshot.llm_view()` (mã, tên, trạng thái việc; tên ngày) —
không có tên, email, phòng ban của nhân viên (quyết định 3, mục 0.1).
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.observability.call_metrics import call_context
from src.services.viga.guardrail_input import INJECTION_DEFENSE_NOTE, wrap_user_input
from src.services.viga.snapshot import JourneySnapshot
from src.services.viga.tools import TASK_TOOLS, TOOL_NAMES

# Dưới ngưỡng này thì coi như LLM không chắc: rơi về hỏi đáp tài liệu thay vì dùng công cụ.
CONFIDENCE_THRESHOLD = 0.55
MAX_CLARIFY_CHARS = 200
MAX_DAY = 31
HISTORY_TURN_MAX_CHARS = 300
ROUTE_OPERATION = "viga.route"

SYSTEM_PROMPT = f"""Bạn là bộ định tuyến của trợ lý Viga cho nhân sự mới. Nhiệm vụ DUY NHẤT: chọn MỘT công cụ trong danh sách
dưới đây cho câu hỏi của người dùng và điền tham số. KHÔNG trả lời câu hỏi.

Công cụ (chỉ dùng đúng tên):
- get_next_tasks: "tiếp theo làm gì", "việc nào làm được ngay". Không tham số.
- get_day_plan: "hôm nay/ngày mai/ngày N có việc gì". args: {{"day": "today" | "tomorrow" | số ngày | null}}.
- explain_lock: "sao tôi chưa làm được việc X", "vì sao việc này bị khóa". args: {{"task_id": mã việc | null}}.
- get_task_detail: "việc X làm thế nào", "hướng dẫn việc này". args: {{"task_id": mã việc | null}}.
- get_progress: "tôi làm được bao nhiêu rồi", "còn bao nhiêu việc". Không tham số.
- search_documents: câu hỏi về nội quy, chính sách, quy trình, phúc lợi, nghỉ phép... cần tra tài liệu. args: {{"query": "câu hỏi"}}.
- none: không công cụ nào hợp (chuyện phiếm, ngoài phạm vi).

Quy tắc: chỉ dùng mã việc (id) có trong danh sách <journey>; không biết việc nào thì để task_id là null.
Câu mô tả một sự cố hay tình huống cụ thể (lỗi đăng nhập, không vào được ứng dụng, thiếu giấy tờ, "thì sao", "phải làm sao"...)
là câu hỏi về nội dung tài liệu: chọn search_documents, KHÔNG đặt clarify. Chỉ đặt clarify (MỘT câu hỏi lại ngắn bằng tiếng
Việt) khi người dùng rõ ràng muốn hỏi về MỘT việc trong lộ trình ("việc này", "việc đó", "bước này") mà không thể biết là việc nào.
{INJECTION_DEFENSE_NOTE}
Chỉ trả JSON đúng schema, không giải thích:
{{"tool": "<tên công cụ>", "args": {{...}}, "confidence": 0.0-1.0, "clarify": null | "câu hỏi lại ngắn"}}"""


@dataclass(frozen=True)
class RouteDecision:
    tool: str  # một tên trong TOOL_NAMES hoặc "none"
    args: dict[str, Any]
    confidence: float
    clarify: str | None = None
    unknown_task: bool = False  # LLM nêu mã việc không thuộc lộ trình của người hỏi


def build_prompt(question: str, snapshot: JourneySnapshot | None, history: Sequence[tuple[str, str]]) -> str:
    parts = [f"<journey>\n{snapshot.llm_view() if snapshot else '(chưa có lộ trình)'}\n</journey>"]
    if history:
        lines = [
            f"{'Người hỏi' if role == 'USER' else 'Viga'}: {text[:HISTORY_TURN_MAX_CHARS]}" for role, text in history
        ]
        parts.append("<history>\n" + "\n".join(lines) + "\n</history>")
    parts.append(wrap_user_input(question))
    return "\n".join(parts)


def _clean_day(value: Any) -> str | int | None:
    if value in ("today", "tomorrow"):
        return str(value)
    if isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= MAX_DAY:
        return value
    return None


def parse_route(raw: str, snapshot: JourneySnapshot | None) -> RouteDecision | None:
    """Kiểm đầu ra của LLM; `None` nếu sai bất kỳ điều gì (người gọi rơi về hỏi đáp tài liệu)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    tool = data.get("tool")
    if not isinstance(tool, str) or (tool not in TOOL_NAMES and tool != "none"):
        return None
    raw_args = data.get("args")
    args: dict[str, Any] = raw_args if isinstance(raw_args, dict) else {}
    confidence = data.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, int | float) or not 0 <= confidence <= 1:
        return None
    clarify = data.get("clarify")
    clarify_text = (
        " ".join(clarify.split())[:MAX_CLARIFY_CHARS] if isinstance(clarify, str) and clarify.strip() else None
    )

    clean: dict[str, Any] = {}
    unknown_task = False
    if tool in TASK_TOOLS:
        task_id = args.get("task_id")
        if isinstance(task_id, int) and not isinstance(task_id, bool):
            if snapshot is not None and snapshot.get(task_id) is not None:
                clean["task_id"] = task_id
            else:
                unknown_task = True  # bịa hoặc của người khác: không dùng, không lộ gì
    elif tool == "get_day_plan":
        clean["day"] = _clean_day(args.get("day"))
    elif tool == "search_documents":
        query = args.get("query")
        if isinstance(query, str) and query.strip():
            clean["query"] = query.strip()[:300]
    return RouteDecision(tool, clean, float(confidence), clarify_text, unknown_task)


async def route_question(
    question: str,
    llm: ChatCompletionPort,
    snapshot: JourneySnapshot | None,
    history: Sequence[tuple[str, str]] = (),
) -> RouteDecision | None:
    """Một lần gọi LLM định tuyến. Mọi lỗi (mạng, JSON sai, kiểm chứng không qua) trả None: người gọi lùi về hỏi đáp tài liệu."""
    try:
        with call_context(operation=ROUTE_OPERATION):
            raw = await llm.complete_json(
                system_prompt=SYSTEM_PROMPT, user_prompt=build_prompt(question, snapshot, history)
            )
    except Exception:
        return None
    return parse_route(raw, snapshot)
