"""Gạch chéo thoát do bộ đọc tài liệu thêm vào (`VinIT\\_BO`, `\\(CCCD\\)`) không được lọt ra câu trả lời hay nội dung task."""

import pytest

from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.text_match import unescape_markdown
from src.services.viga.answer_service import Claim, QuestionEvidence
from src.services.viga.validator import validate_claim


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("https://x.vn/sites/VinIT\\_BO\\_HRBP/a", "https://x.vn/sites/VinIT_BO_HRBP/a"),
        ("Căn cước công dân \\(CCCD\\) bản gốc", "Căn cước công dân (CCCD) bản gốc"),
        ("\\*\\*không in đậm\\*\\*", "**không in đậm**"),
        ("Không có gạch thoát", "Không có gạch thoát"),
        (
            "Đường dẫn C:\\Users giữ nguyên",
            "Đường dẫn C:\\Users giữ nguyên",
        ),  # gạch chéo trước chữ thường không phải thoát Markdown
    ],
)
def test_unescape_markdown(raw: str, clean: str) -> None:
    assert unescape_markdown(raw) == clean


def test_validator_cleans_escapes_in_the_answer_text() -> None:
    content = "Chi tiết hơn ở https://x.vn/VinIT\\_BO\\_HRBP/a và liên hệ Phòng đào tạo."
    section = SectionEvidence(
        section_id=7,
        heading="Nội quy",
        content=content,
        token_count=20,
        chunk_ids=(3,),
        score=0.9,
        document_title="Hướng dẫn ngày 1",
        version_label="1.0",
        document_url="x",
        version_id=1,
    )
    claim = Claim(
        "Nội quy ở đâu?",
        "ANSWER",
        None,
        "Xem tại https://x.vn/VinIT\\_BO\\_HRBP/a",
        "Chi tiết hơn ở https://x.vn/VinIT_BO_HRBP/a",
        3,
    )

    result = validate_claim(claim, {"Nội quy ở đâu?": QuestionEvidence("Nội quy ở đâu?", [section])})

    assert result.response_type == "ANSWER"
    assert result.text == "Xem tại https://x.vn/VinIT_BO_HRBP/a"
