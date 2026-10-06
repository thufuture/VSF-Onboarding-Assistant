"""Dựng user prompt cho `answer_with_claims` — tách khỏi `answer_service.py` vì đây là trách nhiệm riêng
(dựng chuỗi) so với gọi LLM/parse kết quả, và đủ phức tạp để test riêng không cần mock LLM.

Cấu trúc theo slide `day08-rag-pipeline` (mục Augmentation): tách System/Context/Question bằng tag rõ ràng
để model không lẫn dữ liệu tài liệu với chỉ dẫn — xem
docs/chatbot-vsf/plan/phase-2/2-e-prompt-guardrail-rerank/02-augmentation.md mục 3.1, 3.3.

Thứ tự đoạn: GIỮ NGUYÊN thứ tự RRF (điểm cao nhất trước) — KHÔNG đảo "best-first-and-last". Đã cân nhắc
và hoãn (xem 02-augmentation.md mục 3.2): với chỉ ~3-5 đoạn trong `SECTION_TOKEN_BUDGET`, đảo thứ tự là một
thay đổi chưa có số đo chứng minh chiều nào tốt hơn — giữ nguyên để dễ kiểm chứng/debug (đoạn #1 trong
prompt luôn là đoạn điểm cao nhất).

Token budget: SECTION_TOKEN_BUDGET (hybrid_search.py) ~3000 token cho context, cộng thêm system prompt
(~300 token), câu hỏi (~100 token/câu con, tối đa MAX_SUBQUESTIONS câu — query_rewrite.py), output JSON dự
kiến (~500 token) — tổng vẫn nằm trong ngân sách an toàn của DeepSeek. Không cần cấu hình gì thêm ở đây.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.services.retrieval.hybrid_search import SectionEvidence
    from src.services.viga.answer_service import QuestionEvidence


def _format_section(section: SectionEvidence) -> str:
    chunk_id = section.chunk_ids[0] if section.chunk_ids else "?"
    heading = section.heading or "(không có tiêu đề)"
    header = f"[Đoạn — chunk_id={chunk_id} — {section.document_title} — bản {section.version_label} — {heading}]"
    return f"{header}\n{section.content}"


def build_user_prompt(items: list[QuestionEvidence]) -> str:
    parts: list[str] = []
    for index, item in enumerate(items, start=1):
        if item.sections:
            context = "\n\n".join(_format_section(section) for section in item.sections)
        else:
            context = "(không tìm thấy đoạn tài liệu nào liên quan)"
        parts.append(f'<context>\n{context}\n</context>\n<question id="{index}">{item.question}</question>')
    return "\n\n".join(parts)
