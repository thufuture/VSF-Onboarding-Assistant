"""Đơn vị cho `limit_context`: mặc định không đổi gì; dedupe và trần token giữ ít nhất một section mỗi câu hỏi."""

from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.viga.answer_service import QuestionEvidence
from src.services.viga.context_limit import limit_context


def _section(section_id: int, tokens: int = 100) -> SectionEvidence:
    return SectionEvidence(
        section_id=section_id,
        heading=f"h{section_id}",
        content="x",
        token_count=tokens,
        chunk_ids=(section_id * 10,),
        score=1.0,
        document_title="d",
        version_label="v1",
        document_url="u",
        version_id=1,
    )


def _ids(items: list[QuestionEvidence]) -> list[list[int]]:
    return [[s.section_id for s in item.sections] for item in items]


def test_disabled_returns_same_items() -> None:
    items = [QuestionEvidence("a", [_section(1), _section(2)])]

    assert limit_context(items) is items


def test_dedupe_drops_sections_already_seen() -> None:
    items = [QuestionEvidence("a", [_section(1), _section(2)]), QuestionEvidence("b", [_section(2), _section(3)])]

    assert _ids(limit_context(items, dedupe=True)) == [[1, 2], [3]]


def test_dedupe_keeps_first_section_when_everything_repeats() -> None:
    items = [QuestionEvidence("a", [_section(1)]), QuestionEvidence("b", [_section(1)])]

    assert _ids(limit_context(items, dedupe=True)) == [[1], [1]]


def test_total_cap_is_split_between_questions_and_keeps_first_section() -> None:
    items = [
        QuestionEvidence("a", [_section(1, 150), _section(2, 150)]),
        QuestionEvidence("b", [_section(3, 500), _section(4, 50)]),
    ]

    assert _ids(limit_context(items, total_token_cap=400)) == [[1], [3]]


def test_empty_question_stays_empty() -> None:
    items = [QuestionEvidence("a", []), QuestionEvidence("b", [_section(1)])]

    assert _ids(limit_context(items, dedupe=True, total_token_cap=300)) == [[], [1]]
