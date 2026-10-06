"""Đề xuất task bằng AI: độ phủ, thứ tự, tiên quyết, trích dẫn (báo cáo kiểm tra 02/10). Không cần DB: dùng phiên giả."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.services.portal.ai_task_service import COVERAGE_MARKER, propose_tasks_detailed
from src.services.portal.proposal_options import ProposalOptions

LEGACY = ProposalOptions(mode="legacy")  # các test này kiểm đường cũ (suy luận bật, AI chép quote)


class _Rows:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class _Session:
    """Chỉ đủ cho `propose_tasks_detailed`: danh sách section và slug danh mục."""

    def __init__(self, sections: list[Any], slug: str | None = "onboarding") -> None:
        self._sections = sections
        self._slug = slug

    async def scalars(self, _query: object) -> _Rows:
        return _Rows(self._sections)

    async def scalar(self, _query: object) -> str | None:
        return self._slug


def _section(section_id: int, index: int, heading: str, content: str) -> Any:
    return SimpleNamespace(
        id=section_id, section_index=index, heading=heading, content=content, token_count=max(1, len(content) // 4)
    )


HOSO = _section(
    11,
    2,
    "2. Chuẩn bị hồ sơ",
    "* CV.\n* Lý lịch tư pháp (bản chính, còn hạn 3 tháng).\n* Căn cước công dân bản gốc.",
)
HOPDONG = _section(
    12, 5, "5. Ký hợp đồng", "HR gửi hợp đồng qua email, nhân viên ký và gửi lại trước cuối ngày làm việc."
)
LAPTOP = _section(
    13, 8, "8. Nhận laptop", "Nhận laptop tại tầng 12 và đăng nhập Outlook, Teams trước khi làm việc tiếp theo."
)
NGAN = _section(14, 9, "9. Lời chào", "Chào mừng.")


def _task(title: str, section: Any, quote: str, **extra: Any) -> dict[str, Any]:
    return {
        "title": title,
        "summary": f"Tóm tắt {title}",
        "instructions_markdown": "Bước 1.",
        "done_criteria": ["Xong"],
        "estimated_minutes": 10,
        "source_chunks": [{"document_section_id": section.id, "quote": quote}],
        "confidence": "HIGH",
        "warnings": [],
        **extra,
    }


def _llm(first: list[dict[str, Any]], coverage: list[dict[str, Any]] | None = None) -> FakeChatCompletion:
    def respond(system_prompt: str, _user_prompt: str) -> str:
        if COVERAGE_MARKER in system_prompt:
            return json.dumps(coverage or [])
        return json.dumps(first)

    return FakeChatCompletion(respond)


async def test_quote_without_markdown_markers_is_accepted_and_returned_clean() -> None:
    llm = _llm([_task("Nộp hồ sơ", HOSO, "CV. Lý lịch tư pháp (bản chính, còn hạn 3 tháng).")])

    result = await propose_tasks_detailed(_Session([HOSO]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ"]
    chunk = result.proposals[0].source_chunks[0]
    assert chunk.quote == "CV. Lý lịch tư pháp (bản chính, còn hạn 3 tháng)."
    assert chunk.heading == "2. Chuẩn bị hồ sơ"
    assert result.proposals[0].task_group == "PROFILE"  # nhóm mặc định theo danh mục


async def test_proposal_with_invented_quote_is_dropped() -> None:
    llm = _llm([_task("Nộp hồ sơ", HOSO, "Nộp hộ chiếu bản sao có công chứng")])

    result = await propose_tasks_detailed(_Session([HOSO]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert result.proposals == []
    assert [item.section_id for item in result.uncovered] == [HOSO.id]


async def test_uncited_sections_get_a_second_pass_and_are_placed_by_document_position() -> None:
    llm = _llm(
        [_task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12")],
        coverage=[_task("Nộp hồ sơ", HOSO, "Lý lịch tư pháp (bản chính, còn hạn 3 tháng)")],
    )

    result = await propose_tasks_detailed(_Session([HOSO, LAPTOP]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop"]  # hồ sơ nằm trước laptop trong tài liệu
    assert [p.order for p in result.proposals] == [1, 2]
    assert result.uncovered == []


async def test_sections_still_without_task_are_reported_but_heading_only_sections_are_not() -> None:
    llm = _llm([_task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12")], coverage=[])

    result = await propose_tasks_detailed(
        _Session([HOSO, HOPDONG, LAPTOP, NGAN]),  # type: ignore[arg-type]
        document_version_id=1,
        llm=llm,
        options=LEGACY,
    )

    assert [item.section_id for item in result.uncovered] == [HOSO.id, HOPDONG.id]


async def test_ai_order_wins_over_document_order_for_first_pass() -> None:
    llm = _llm(
        [
            _task("Ký hợp đồng", HOPDONG, "ký và gửi lại trước cuối ngày", order=3),
            _task("Nộp hồ sơ", HOSO, "Căn cước công dân bản gốc", order=1),
            _task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12", order=2),
        ]
    )

    result = await propose_tasks_detailed(
        _Session([HOSO, HOPDONG, LAPTOP]), document_version_id=1, llm=llm, options=LEGACY
    )  # type: ignore[arg-type]

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop", "Ký hợp đồng"]
    assert [p.order for p in result.proposals] == [1, 2, 3]


async def test_prerequisites_keep_only_earlier_real_tasks() -> None:
    llm = _llm(
        [
            _task(
                "Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12", order=1, prerequisites=["Ký hợp đồng"]
            ),  # trỏ tới sau
            _task(
                "Ký hợp đồng",
                HOPDONG,
                "ký và gửi lại trước cuối ngày",
                order=2,
                prerequisites=["Nhận laptop", "Không có"],
            ),
            _task("Nộp hồ sơ", HOSO, "Căn cước công dân bản gốc", order=3, prerequisites=["Nộp hồ sơ"]),  # tự trỏ
        ]
    )

    result = await propose_tasks_detailed(
        _Session([HOSO, HOPDONG, LAPTOP]), document_version_id=1, llm=llm, options=LEGACY
    )  # type: ignore[arg-type]

    by_title = {p.title: p for p in result.proposals}
    assert by_title["Nhận laptop"].prerequisites == []
    assert by_title["Ký hợp đồng"].prerequisites == ["Nhận laptop"]
    assert by_title["Nộp hồ sơ"].prerequisites == []


@pytest.mark.parametrize("bad_order", ["hai", None, [1], {"a": 1}])
async def test_unreadable_order_does_not_drop_the_proposal(bad_order: object) -> None:
    llm = _llm([_task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12", order=bad_order)])

    result = await propose_tasks_detailed(_Session([LAPTOP]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert [p.title for p in result.proposals] == ["Nhận laptop"]
    assert result.proposals[0].order == 1  # được đánh số lại theo thứ tự cuối cùng


async def test_detail_missing_from_the_instructions_is_flagged_for_hr() -> None:
    llm = _llm([_task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12", instructions_markdown="Nhận laptop.")])

    result = await propose_tasks_detailed(_Session([LAPTOP]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert any("tầng 12" in note for note in result.proposals[0].review_notes)
    assert result.proposals[0].warnings == []  # không lẫn vào phần Lưu ý hiện cho nhân viên


async def test_detail_mentioned_in_the_instructions_is_not_flagged() -> None:
    llm = _llm(
        [_task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12", instructions_markdown="Nhận laptop tại tầng 12.")]
    )

    result = await propose_tasks_detailed(_Session([LAPTOP]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert result.proposals[0].review_notes == []


async def test_quote_taken_from_the_heading_is_accepted_when_the_content_is_only_a_condition() -> None:
    """Tài liệu thật có mục mà việc cần làm nằm ở tiêu đề, nội dung chỉ là điều kiện: trích tiêu đề không bị loại oan."""
    section = _section(
        15,
        8,
        "Nhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR",
        "Sau khi có laptop và đăng nhập được outlook và teams thì mới tiếp tục bước tiếp theo.",
    )
    llm = _llm([_task("Nhận laptop", section, "Nhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR")])

    result = await propose_tasks_detailed(_Session([section]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    assert [p.title for p in result.proposals] == ["Nhận laptop"]
    assert result.uncovered == []
