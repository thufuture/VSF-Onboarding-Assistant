"""Kiểm claim trước khi hiển thị: `chunk_id` phải thuộc lượt tìm kiếm của đúng câu hỏi con đó (INV6),
`quote` phải là chuỗi con nguyên văn của section cha chứa chunk đó (INV13, sau khi bỏ ký hiệu Markdown,
gộp khoảng trắng và không phân biệt hoa thường: xem `services/text_match.py`). Claim không qua kiểm tra bị ép về `NO_BASIS` — không bao giờ hiển thị câu trả lời chưa
kiểm chứng (mục 6, kế hoạch 2-C/2-D mở rộng).
"""

from __future__ import annotations

from dataclasses import replace

from src.services.text_match import quote_matches, tidy_quote, unescape_markdown
from src.services.viga.answer_service import Claim, QuestionEvidence


def validate_claim(claim: Claim, evidence_by_question: dict[str, QuestionEvidence]) -> Claim:
    if claim.response_type != "ANSWER":
        return claim  # NO_BASIS không cần quote/chunk_id — hợp lệ nguyên trạng

    item = evidence_by_question.get(claim.question)
    if item is None or not claim.quote or claim.chunk_id is None:
        return Claim(claim.question, "NO_BASIS", "validation_failed", None, None, None)

    section_by_chunk = {cid: section for section in item.sections for cid in section.chunk_ids}
    section = section_by_chunk.get(claim.chunk_id)
    if section is None:  # INV6: chunk_id phải thuộc tập chunk đã truy xuất cho ĐÚNG câu hỏi con này
        return Claim(claim.question, "NO_BASIS", "validation_failed", None, None, None)

    # INV13 (so khớp trên chữ, bỏ ký hiệu Markdown). Tiêu đề mục cũng là chữ của mục (đã hiện cho mô hình ở đầu đoạn): tài liệu thật
    # có điều kiện áp dụng nằm ngay tiêu đề, vd. "(bắt buộc cho CBNV mới)", "Dành cho văn phòng Vincom Đồng Khởi".
    if not quote_matches(claim.quote, f"{section.heading or ''}\n{section.content}"):
        return Claim(claim.question, "NO_BASIS", "validation_failed", None, None, None)

    tidy = tidy_quote(claim.quote)
    text = unescape_markdown(claim.text) if claim.text else claim.text
    if tidy == claim.quote and text == claim.text:
        return claim
    return replace(claim, quote=tidy, text=text)


def validate_claims(claims: list[Claim], items: list[QuestionEvidence]) -> list[Claim]:
    evidence_by_question = {item.question: item for item in items}
    return [validate_claim(claim, evidence_by_question) for claim in claims]
