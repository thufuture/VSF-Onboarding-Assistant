"""Đơn vị cho validate_claim (mục 6, kế hoạch 2-C/2-D mở rộng): quote đúng/sai/thiếu 1 chữ, chunk_id lạ,
chunk_id thuộc câu hỏi con khác (INV6), NO_BASIS giữ nguyên."""

from src.services.chat.answer_service import Claim, QuestionEvidence
from src.services.chat.validator import validate_claim, validate_claims
from src.services.retrieval.hybrid_search import SectionEvidence

_SECTION = SectionEvidence(
    section_id=62,
    heading="5.1 Mức hưởng",
    content="Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.",
    token_count=12,
    chunk_ids=(10,),
    score=0.9,
    document_title="Chính sách nghỉ phép năm",
    version_label="2.0",
    document_url="https://res.cloudinary.com/demo/raw/upload/leave-policy.docx",
    version_id=1,
)
_OTHER_SECTION = SectionEvidence(
    section_id=99,
    heading="Mục khác",
    content="Nội dung hoàn toàn khác, không liên quan.",
    token_count=6,
    chunk_ids=(20,),
    score=0.5,
    document_title="Tài liệu khác",
    version_label="1.0",
    document_url="https://res.cloudinary.com/demo/raw/upload/other-doc.docx",
    version_id=2,
)


def _evidence(question: str, sections: list[SectionEvidence]) -> dict[str, QuestionEvidence]:
    item = QuestionEvidence(question, sections)
    return {item.question: item}


def test_correct_quote_and_chunk_id_passes() -> None:
    claim = Claim("Q1", "ANSWER", None, "12 ngày", "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.", 10)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "ANSWER"
    assert result is claim


def test_fabricated_quote_is_rejected() -> None:
    claim = Claim("Q1", "ANSWER", None, "20 ngày", "Câu này hoàn toàn không có trong tài liệu gốc.", 10)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "NO_BASIS"
    assert result.reason_code == "validation_failed"


def test_quote_missing_one_word_is_rejected() -> None:
    claim = Claim(
        "Q1", "ANSWER", None, "x", "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm.", 10
    )  # thiếu "có lương"

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "NO_BASIS"


def test_unknown_chunk_id_is_rejected() -> None:
    claim = Claim("Q1", "ANSWER", None, "x", "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.", 999)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "NO_BASIS"


def test_chunk_id_belonging_to_a_different_question_is_rejected() -> None:
    # INV6: chunk_id=20 tồn tại thật, nhưng thuộc evidence của MỘT câu hỏi khác, không phải "Q1".
    claim = Claim("Q1", "ANSWER", None, "x", "Nội dung hoàn toàn khác, không liên quan.", 20)
    evidence = _evidence("Q1", [_SECTION])  # Q1 chỉ có _SECTION (chunk 10), không có chunk 20

    result = validate_claim(claim, evidence)

    assert result.response_type == "NO_BASIS"


def test_no_basis_claim_passes_through_unchanged() -> None:
    claim = Claim("Q1", "NO_BASIS", "out_of_scope", None, None, None)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result is claim


def test_answer_without_quote_is_rejected() -> None:
    claim = Claim("Q1", "ANSWER", None, "text thôi", None, 10)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "NO_BASIS"


def test_validate_claims_handles_multiple_independently() -> None:
    good = Claim("Q1", "ANSWER", None, "x", "Mỗi nhân viên chính thức được hưởng 12 ngày phép năm có lương.", 10)
    bad = Claim("Q2", "ANSWER", None, "x", "bịa hoàn toàn", 999)
    items = [QuestionEvidence("Q1", [_SECTION]), QuestionEvidence("Q2", [_OTHER_SECTION])]

    results = validate_claims([good, bad], items)

    assert results[0].response_type == "ANSWER"
    assert results[1].response_type == "NO_BASIS"


def test_quote_missing_markdown_markers_still_passes_and_is_returned_clean() -> None:
    section = SectionEvidence(
        section_id=7,
        heading="2. Hồ sơ",
        content="* CV.\n* Lý lịch tư pháp (bản chính).\n",
        token_count=8,
        chunk_ids=(30,),
        score=0.8,
        document_title="Hướng dẫn ngày 1",
        version_label="1.0",
        document_url="https://res.cloudinary.com/demo/raw/upload/day1.docx",
        version_id=3,
    )
    claim = Claim("Q1", "ANSWER", None, "CV", "CV. Lý lịch tư pháp (bản chính).", 30)

    result = validate_claim(claim, _evidence("Q1", [section]))

    assert result.response_type == "ANSWER"
    assert result.quote == "CV. Lý lịch tư pháp (bản chính)."


def test_quote_taken_from_the_section_heading_is_accepted() -> None:
    """Điều kiện áp dụng nằm ngay tiêu đề mục (vd. "(bắt buộc cho CBNV mới)") là chữ của mục, trích được."""
    section = SectionEvidence(
        section_id=9,
        heading="Tham gia chương trình Đào tạo Hội nhập (bắt buộc cho CBNV mới)",
        content="* Điểm danh đầu giờ.\n* Đạt >= 80% bài test cuối khóa.",
        token_count=14,
        chunk_ids=(40,),
        score=0.8,
        document_title="Hướng dẫn ngày 1",
        version_label="1.0",
        document_url="x",
        version_id=3,
    )
    claim = Claim("Có bắt buộc không?", "ANSWER", None, "Có, bắt buộc.", "Đào tạo Hội nhập (bắt buộc cho CBNV mới)", 40)

    result = validate_claim(claim, _evidence("Có bắt buộc không?", [section]))

    assert result.response_type == "ANSWER"


def test_quote_with_invented_words_is_still_rejected_after_normalization() -> None:
    claim = Claim("Q1", "ANSWER", None, "13 ngày", "Mỗi nhân viên chính thức được hưởng 13 ngày phép năm có lương.", 10)

    result = validate_claim(claim, _evidence("Q1", [_SECTION]))

    assert result.response_type == "NO_BASIS"
    assert result.reason_code == "validation_failed"
