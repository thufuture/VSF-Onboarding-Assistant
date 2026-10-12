"""Giới hạn ngữ cảnh đưa vào bước trả lời (tối ưu từ benchmark 10/2026: ~57 section mỗi câu, chỉ ~2% là section đúng).

Mỗi câu hỏi con tìm riêng nên câu kép nhân ngữ cảnh lên và cùng một section có thể xuất hiện nhiều lần trong prompt.
Hai bước ở đây chạy sau khi tìm xong, trước khi dựng prompt, và đều TẮT theo mặc định (xem `config.py`):

- `dedupe`: section đã có ở câu hỏi con trước thì không đưa lại. Câu nào bị lấy hết section vẫn giữ section đầu của nó,
  để LLM không kết luận "không có tài liệu" chỉ vì phần trùng.
- `total_token_cap`: trần tổng token ngữ cảnh của cả lượt, chia đều cho các câu hỏi con; mỗi câu luôn giữ ít nhất section đầu.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.retrieval.hybrid_search import SectionEvidence
    from src.services.viga.answer_service import QuestionEvidence


def limit_context(
    items: list[QuestionEvidence], *, dedupe: bool = False, total_token_cap: int = 0
) -> list[QuestionEvidence]:
    if not items or not (dedupe or total_token_cap > 0):
        return items
    seen: set[int] = set()
    per_question_cap = total_token_cap // len(items) if total_token_cap > 0 else 0
    limited: list[QuestionEvidence] = []
    for item in items:
        sections: list[SectionEvidence] = list(item.sections)
        if dedupe and sections:
            fresh = [s for s in sections if s.section_id not in seen]
            sections = fresh or sections[:1]
        if per_question_cap > 0 and sections:
            kept: list[SectionEvidence] = []
            used = 0
            for section in sections:
                if kept and used + section.token_count > per_question_cap:
                    break
                kept.append(section)
                used += section.token_count
            sections = kept
        seen.update(s.section_id for s in sections)
        limited.append(replace(item, sections=sections))
    return limited
