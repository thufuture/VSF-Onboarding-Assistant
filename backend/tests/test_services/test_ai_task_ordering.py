"""Thứ tự task AI đề xuất: việc "cuối ngày" xếp cuối; gạch chéo thoát Markdown được làm sạch."""

import json
from types import SimpleNamespace
from typing import Any

from src.infrastructure.ai.fake_chat_completion import FakeChatCompletion
from src.services.portal.ai_task_service import propose_tasks_detailed
from src.services.portal.proposal_options import ProposalOptions

LEGACY = ProposalOptions(mode="legacy")  # các test này kiểm đường cũ (suy luận bật, AI chép quote)


class _Rows:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class _Session:
    def __init__(self, sections: list[Any]) -> None:
        self._sections = sections

    async def scalars(self, _query: object) -> _Rows:
        return _Rows(self._sections)

    async def scalar(self, _query: object) -> str | None:
        return None


def _section(section_id: int, index: int, heading: str, content: str) -> Any:
    return SimpleNamespace(id=section_id, section_index=index, heading=heading, content=content, token_count=30)


def _task(title: str, section: Any, quote: str, order: int, **extra: Any) -> dict[str, Any]:
    return {
        "title": title,
        "summary": f"Tóm tắt {title}",
        "instructions_markdown": "Bước 1.",
        "done_criteria": ["Xong"],
        "estimated_minutes": 10,
        "source_chunks": [{"document_section_id": section.id, "quote": quote}],
        "confidence": "HIGH",
        "warnings": [],
        "order": order,
        **extra,
    }


HOP_DONG = _section(
    1, 5, "Ký hợp đồng", "CUỐI NGÀY sẽ có email hướng dẫn ký hợp đồng lao động, ký trong thời gian quy định."
)
LAPTOP = _section(2, 8, "Nhận laptop", "Nhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR trong ngày đầu.")
TU = _section(3, 17, "Tủ gửi đồ", "Gửi yêu cầu tủ gửi đồ theo mẫu request tủ gửi đồ của khối.")


async def test_end_of_day_tasks_go_last_even_when_the_model_orders_them_earlier() -> None:
    llm = FakeChatCompletion(
        json.dumps(
            [
                _task("Ký hợp đồng lao động", HOP_DONG, "CUỐI NGÀY sẽ có email hướng dẫn ký hợp đồng lao động", 1),
                _task("Nhận laptop", LAPTOP, "Nhận laptop tại tầng 12 theo chỉ dẫn của ITHD và HR", 2),
                _task("Đăng ký tủ gửi đồ", TU, "Gửi yêu cầu tủ gửi đồ theo mẫu request tủ gửi đồ của khối", 3),
            ]
        )
    )

    result = await propose_tasks_detailed(
        _Session([HOP_DONG, LAPTOP, TU]),  # type: ignore[arg-type]
        document_version_id=1,
        llm=llm,
        options=LEGACY,
    )

    assert [p.title for p in result.proposals] == ["Nhận laptop", "Đăng ký tủ gửi đồ", "Ký hợp đồng lao động"]
    assert [p.order for p in result.proposals] == [1, 2, 3]


async def test_markdown_escapes_copied_from_the_source_are_cleaned_in_the_proposal() -> None:
    section = _section(
        4, 7, "Nội quy", "Xem chi tiết tại https://x.vn/VinIT\\_BO\\_HRBP/a để biết thêm nội quy công ty."
    )
    llm = FakeChatCompletion(
        json.dumps(
            [
                _task(
                    "Nghe nội quy",
                    section,
                    "Xem chi tiết tại https://x.vn/VinIT\\_BO\\_HRBP/a",
                    1,
                    instructions_markdown="Xem tại https://x.vn/VinIT\\_BO\\_HRBP/a",
                )
            ]
        )
    )

    result = await propose_tasks_detailed(_Session([section]), document_version_id=1, llm=llm, options=LEGACY)  # type: ignore[arg-type]

    proposal = result.proposals[0]
    assert proposal.instructions_markdown == "Xem tại https://x.vn/VinIT_BO_HRBP/a"
    assert proposal.source_chunks[0].quote == "Xem chi tiết tại https://x.vn/VinIT_BO_HRBP/a"
    assert proposal.review_notes == []  # đường dẫn có trong hướng dẫn nên không bị nhắc là thiếu
