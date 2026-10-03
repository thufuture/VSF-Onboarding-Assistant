"""Hồi quy từ bộ kiểm tra thật (báo cáo 02/10): các mục nhiều dòng `* ...` của tài liệu "Hướng dẫn ngày 1" từng làm câu trả lời của Viga
và đề xuất task bị loại oan vì mô hình trích lại bằng chữ liền (bỏ `* `). Nội dung dưới đây là nguyên văn mục trong DB lúc kiểm tra."""

import pytest

from src.services.chat.answer_service import Claim, QuestionEvidence
from src.services.chat.validator import validate_claim
from src.services.retrieval.hybrid_search import SectionEvidence
from src.services.text_match import quote_matches

HO_SO = (
    "* CV.\n* Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp.\n* Giấy khám sức khỏe\n"
    "* Hình ảnh xác nhận nơi cư trú (bản photo, có thể chụp ảnh VNeID định danh mức 2).\n"
    "* Căn cước công dân bản Photo.\n* Chứng chỉ bang cấp chuyên môn bắt buộc.\n* Đầu mối liên hệ: Phòng tuyển dụng."
)
DAO_TAO = (
    "* Điều kiện được tính hoàn thành:\n* Điểm danh đầu giờ.\n* Hoàn thành Khảo sát sau chương trình đào tạo\n"
    "* Hoàn thành và đạt >= 80% bài test cuối khóa.\n\nĐầu mối: v.thudq@vinsmartfuture.tech (Phòng ĐT&PTVH)"
)
FORM_T3 = (
    "To: email của T3 ( Ở Khối KD và VH Vinmec là anh Dương Anh Nghi (v.dir.data3@vinsmartfuture.tech) )\n\n"
    "Title: Xin phê duyệt [Nội dung cần phê duyệt] - [họ và tên] -[mã nhân viên]\n\ns\n\nKính gửi:\n\nTôi là\n\n"
    "Thông tin chi tiết:\n\n* Mục đích sử dụng:\n* Đơn vị công tác:\n\nKính mong Lãnh đạo xem xét và phê duyệt."
)


@pytest.mark.parametrize(
    ("content", "quote"),
    [
        (HO_SO, "CV. Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp. Giấy khám sức khỏe"),
        (HO_SO, "Căn cước công dân bản Photo. Chứng chỉ bang cấp chuyên môn bắt buộc."),
        (HO_SO, "Hình ảnh xác nhận nơi cư trú (bản photo, có thể chụp ảnh VNeID định danh mức 2)."),
        (HO_SO, "* Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp.\n* Giấy khám sức khỏe"),
        (HO_SO, "Đầu mối liên hệ: Phòng tuyển dụng"),
        (DAO_TAO, "Điều kiện được tính hoàn thành: Điểm danh đầu giờ. Hoàn thành Khảo sát sau chương trình đào tạo"),
        (DAO_TAO, "Hoàn thành và đạt >= 80% bài test cuối khóa."),
        (DAO_TAO, "Đầu mối: v.thudq@vinsmartfuture.tech (Phòng ĐT&PTVH)"),
        (FORM_T3, "Title: Xin phê duyệt [Nội dung cần phê duyệt] - [họ và tên] -[mã nhân viên]"),
        (FORM_T3, "Mục đích sử dụng: Đơn vị công tác:"),
    ],
)
def test_model_style_quotes_of_the_real_sections_are_accepted(content: str, quote: str) -> None:
    assert quote_matches(quote, content)


@pytest.mark.parametrize(
    ("content", "quote"),
    [
        (HO_SO, "Hộ chiếu bản gốc có công chứng"),
        (HO_SO, "Căn cước công dân bản gốc"),  # đổi chữ "Photo" thành "gốc": nội dung khác
        (DAO_TAO, "Hoàn thành và đạt >= 90% bài test cuối khóa."),
        (DAO_TAO, "Đầu mối: v.khac@vinsmartfuture.tech"),
        (FORM_T3, "Title: Xin nghỉ phép - [họ và tên]"),
    ],
)
def test_quotes_with_changed_facts_are_still_rejected(content: str, quote: str) -> None:
    assert not quote_matches(quote, content)


def _section(content: str) -> SectionEvidence:
    return SectionEvidence(
        section_id=2,
        heading="Chuẩn bị hồ sơ phải nộp trong ngày đầu",
        content=content,
        token_count=60,
        chunk_ids=(7,),
        score=0.9,
        document_title="Huong_dan_ngay_1_onboarding",
        version_label="1.0",
        document_url="x",
        version_id=1,
    )


def test_validator_keeps_the_answer_and_cleans_the_quote_for_display() -> None:
    """Trước đây câu "Hồ sơ cần nộp gồm gì?" lúc đúng lúc "chưa có căn cứ" tùy mô hình có trích kèm `* ` hay không."""
    claim = Claim(
        "Hồ sơ cần nộp?",
        "ANSWER",
        None,
        "Bạn nộp CV, lý lịch tư pháp, giấy khám sức khỏe.",
        "* CV.\n* Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp.\n* Giấy khám sức khỏe",
        7,
    )
    evidence = {"Hồ sơ cần nộp?": QuestionEvidence("Hồ sơ cần nộp?", [_section(HO_SO)])}

    result = validate_claim(claim, evidence)

    assert result.response_type == "ANSWER"
    assert result.quote == "• CV. • Lý lịch tư pháp, hoặc giấy hẹn lấy lý lịch tư pháp. • Giấy khám sức khỏe"
