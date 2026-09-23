"""`rerank()` là passthrough (quyết định D5: chưa bật rerank cho MVP) — chỉ kiểm không đổi nội dung/thứ tự."""

from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.retrieval.rerank import rerank


def _section(section_id: int) -> SectionEvidence:
    return SectionEvidence(
        section_id=section_id,
        heading="h",
        content="c",
        token_count=1,
        chunk_ids=(section_id,),
        score=1.0,
        document_title="d",
        version_label="v1",
        document_url="https://res.cloudinary.com/demo/raw/upload/d.docx",
        version_id=1,
    )


def test_returns_same_list_unchanged() -> None:
    sections = [_section(1), _section(2), _section(3)]

    result = rerank(sections, query="bất kỳ")

    assert result == sections


def test_empty_list_stays_empty() -> None:
    assert rerank([], query="bất kỳ") == []
