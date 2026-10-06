"""Lớp chặn và lối tắt TRƯỚC LLM (mục 15.3c, 17.5b): rẻ, tất định, không tốn LLM.

- `is_personal_info_question`: câu hỏi về thông tin cá nhân không có trong tài liệu chung (lương, mentor, chỗ ngồi, số dư phép
  riêng của chính người hỏi) trả thẳng đường OUT_OF_SCOPE, không cho LLM định tuyến "đoán" đó là câu hỏi tài liệu.
- `shortcut_tool`: ba câu rất phổ biến và rõ ("hôm nay làm gì", "tiếp theo làm gì", "tiến độ của tôi") đi thẳng vào công cụ lộ trình.
- `tool_fits_question`: LLM định tuyến đôi khi chọn công cụ lộ trình cho câu hỏi THÔNG TIN ("nhận laptop xong thì làm gì tiếp theo?"
  cần nội dung tài liệu chứ không phải danh sách việc). Công cụ chỉ được dùng khi câu hỏi có dấu hiệu đúng loại; không thì đi hỏi đáp tài liệu.
"""

from __future__ import annotations

import re

from src.services.viga.tools import strip_accents

# Phải có đại từ ngôi thứ nhất để tránh chặn nhầm câu hỏi CHÍNH SÁCH ("lương thử việc tối thiểu bao nhiêu phần trăm?").
_FIRST_PERSON_ACCENTED = re.compile(r"\b(?:tôi|mình|em)\b")
_FIRST_PERSON_PLAIN = re.compile(r"\b(?:toi|minh|em)\b")
_PERSONAL_TOPICS = re.compile(
    r"\b(?:luong|bang luong|thu nhap|mentor|buddy|cho ngoi|so du phep|phep con lai|ngay phep con lai|"
    r"phep nam con|con bao nhieu ngay phep|con may ngay phep|thuong cua|bao hiem cua)\b"
)

_SHORTCUTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "get_next_tasks",
        re.compile(
            r"^(?:tiep theo|buoc tiep theo|viec tiep theo|bat dau tu dau)\b"
            r"|\blam gi tiep\b|\bviec nao lam duoc ngay\b"
        ),
    ),
    ("get_day_plan", re.compile(r"^(?:hom nay|ngay hom nay)(?: (?:toi|minh|em|can|phai))* lam gi$")),
    (
        "get_progress",
        re.compile(
            r"\btien do cua (?:toi|minh)\b|^(?:toi|minh|em) lam duoc bao nhieu\b|^tien do$|^con bao nhieu viec\b"
        ),
    ),
)
_FILLER = re.compile(r"\b(?:cho minh hoi|cho toi hoi|xin hoi|nhe|a|di|vay)\b")
MAX_SHORTCUT_WORDS = 8
MAX_UNANCHORED_SHORTCUT_WORDS = 5

# "xong", "sau khi" cho thấy câu hỏi gắn với một sự kiện trong tài liệu ("nhận laptop xong thì làm gì tiếp theo?").
_CONDITIONAL = re.compile(r"\b(?:xong|sau khi|neu|khi nao)\b")
_ANCHORED_NEXT = re.compile(r"^(?:tiep theo|buoc tiep theo|viec tiep theo|bat dau tu dau)\b")

# "làm thế nào / làm sao" là cách hỏi quen thuộc cho cả tình huống ("T3 chưa trả lời thì tôi làm sao?") lẫn việc cụ thể: cụm yếu này
# chỉ đủ để mở hướng dẫn việc khi câu không nêu tình huống (chưa/không/nếu/thì/lỗi...); tình huống thì tài liệu mới có đáp án.
_STRONG_TASK_DETAIL = re.compile(r"\b(?:huong dan|cac buoc|chi tiet|buoc nao)\b")
_WEAK_TASK_DETAIL = re.compile(r"\b(?:lam the nao|lam sao|cach lam)\b")
_SCENARIO = re.compile(r"\b(?:chua|khong|neu|thi|bi|loi|het han|qua han|mat|sai)\b")

_TOOL_CUES: dict[str, re.Pattern[str]] = {
    "get_task_detail": re.compile(r"\b(?:huong dan|lam the nao|lam sao|cac buoc|cach lam|chi tiet|buoc nao)\b"),
    "explain_lock": re.compile(r"\b(?:khoa|chua lam duoc|vi sao|tai sao|bi chan|chua mo|chua den)\b"),
    "get_day_plan": re.compile(r"\b(?:viec|lam gi|ke hoach|cong viec|task|nhiem vu|lich)\b"),
    "get_next_tasks": re.compile(r"\b(?:tiep theo|tiep|viec nao|lam duoc ngay|bat dau)\b"),
    "get_progress": re.compile(r"\b(?:tien do|bao nhieu|hoan thanh|con lai)\b"),
}


def normalize_question(text: str) -> str:
    """Chữ thường, bỏ dấu, bỏ dấu câu và từ đệm thường gặp để so khớp luật."""
    lowered = strip_accents(text)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", lowered)
    cleaned = _FILLER.sub(" ", cleaned)
    return " ".join(cleaned.split())


def _mentions_self(text: str) -> bool:
    """Có đại từ ngôi thứ nhất không. Bỏ dấu thì "tôi" và "tối" trùng nhau ("lương tối thiểu"), nên câu có dấu được
    kiểm theo chữ có dấu; chỉ câu gõ không dấu mới dùng bản bỏ dấu."""
    lowered = text.lower()
    if lowered != strip_accents(lowered):
        return bool(_FIRST_PERSON_ACCENTED.search(lowered))
    return bool(_FIRST_PERSON_PLAIN.search(lowered))


def is_personal_info_question(text: str) -> bool:
    return bool(_PERSONAL_TOPICS.search(normalize_question(text))) and _mentions_self(text)


def shortcut_tool(text: str) -> str | None:
    """Tên công cụ nếu câu khớp CHẮC CHẮN một lối tắt; không chắc thì None (để LLM định tuyến)."""
    normalized = normalize_question(text)
    if len(normalized.split()) > MAX_SHORTCUT_WORDS:  # câu dài thường có thêm ý khác: không ép vào lối tắt
        return None
    for tool, pattern in _SHORTCUTS:
        if not pattern.search(normalized):
            continue
        if _CONDITIONAL.search(normalized):  # có điều kiện kèm theo: để LLM / tài liệu xử lý
            return None
        if tool == "get_next_tasks" and not _ANCHORED_NEXT.search(normalized):
            if len(normalized.split()) > MAX_UNANCHORED_SHORTCUT_WORDS:  # "lam gi tiep" lọt giữa câu dài
                return None
        return tool
    return None


def tool_fits_question(tool: str, text: str) -> bool:
    """Công cụ lộ trình do LLM chọn có hợp với câu hỏi không. Công cụ lạ hoặc `search_documents` không bị chặn ở đây."""
    cue = _TOOL_CUES.get(tool)
    if cue is None:
        return True
    normalized = normalize_question(text)
    if tool in ("get_next_tasks", "get_day_plan", "get_progress") and _CONDITIONAL.search(normalized):
        return False  # câu hỏi gắn với một sự kiện/điều kiện cụ thể là hỏi nội dung tài liệu
    if tool == "get_task_detail":
        if _STRONG_TASK_DETAIL.search(normalized):
            return True
        return bool(_WEAK_TASK_DETAIL.search(normalized)) and not _SCENARIO.search(normalized)
    return bool(cue.search(normalized))
