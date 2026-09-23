"""Đơn vị cho `build_user_prompt` (mục 3.1/3.3, 2-e-prompt-guardrail-rerank/02-augmentation.md): tag rõ
ràng, metadata nguồn, GIỮ NGUYÊN thứ tự RRF (không đảo best-first-and-last)."""

from src.services.chat.answer_service import QuestionEvidence
from src.services.chat.prompt_builder import build_user_prompt
from src.services.retrieval.hybrid_search import SectionEvidence


def _section(section_id: int, content: str, *, title: str = "Quy định nghỉ phép", version: str = "v1") -> SectionEvidence:
    return SectionEvidence(
        section_id=section_id,
        heading="Nghỉ phép năm",
        content=content,
        token_count=10,
        chunk_ids=(section_id * 10,),
        score=1.0,
        document_title=title,
        version_label=version,
        document_url="https://res.cloudinary.com/demo/raw/upload/doc.docx",
        version_id=1,
    )


def test_wraps_context_and_question_in_tags() -> None:
    items = [QuestionEvidence(question="Nghỉ phép năm bao nhiêu ngày?", sections=[_section(1, "12 ngày.")])]

    prompt = build_user_prompt(items)

    assert "<context>" in prompt and "</context>" in prompt
    assert '<question id="1">Nghỉ phép năm bao nhiêu ngày?</question>' in prompt


def test_includes_document_title_and_version_in_section_header() -> None:
    items = [QuestionEvidence(question="q", sections=[_section(1, "nội dung", title="Sổ tay nhân viên", version="v3")])]

    prompt = build_user_prompt(items)

    assert "Sổ tay nhân viên" in prompt
    assert "bản v3" in prompt


def test_keeps_rrf_order_unchanged() -> None:
    # Không đảo "best-first-and-last" — thứ tự trong prompt phải khớp đúng thứ tự đầu vào (điểm RRF giảm dần).
    items = [
        QuestionEvidence(
            question="q",
            sections=[_section(1, "đoạn điểm cao nhất"), _section(2, "đoạn điểm nhì"), _section(3, "đoạn điểm ba")],
        )
    ]

    prompt = build_user_prompt(items)

    assert prompt.index("đoạn điểm cao nhất") < prompt.index("đoạn điểm nhì") < prompt.index("đoạn điểm ba")


def test_no_sections_shows_explicit_placeholder() -> None:
    items = [QuestionEvidence(question="câu hỏi không có evidence", sections=[])]

    prompt = build_user_prompt(items)

    assert "không tìm thấy đoạn tài liệu nào liên quan" in prompt


def test_multiple_questions_each_get_own_context_and_question_block() -> None:
    items = [
        QuestionEvidence(question="câu 1", sections=[_section(1, "a")]),
        QuestionEvidence(question="câu 2", sections=[_section(2, "b")]),
    ]

    prompt = build_user_prompt(items)

    assert prompt.count("<context>") == 2
    assert '<question id="1">câu 1</question>' in prompt
    assert '<question id="2">câu 2</question>' in prompt
