# mypy: disable-error-code="arg-type"
"""Tạo task cho đúng các mục HR chọn (mục AI đã bỏ qua vì tưởng chỉ có thông tin). Không cần DB: phiên giả và LLM giả."""

import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.services.portal.ai_task_service import propose_tasks_for_sections, section_order
from src.services.portal.errors import PortalError
from src.services.portal.proposal_options import ProposalOptions

OPTIONS = ProposalOptions(mode="fast", batch_words=1000)
AVATAR = SimpleNamespace(
    id=21,
    section_index=4,
    heading="ẢNH ĐẠI DIỆN CHỮ KÝ SLIDE",
    content="Cập nhật ảnh đại diện Teams và cài chữ ký email theo mẫu của công ty trước cuối ngày.",
    token_count=20,
)


class _Session:
    """`scalar` trả lần lượt: các mục được hỏi (theo thứ tự id), cuối cùng là slug danh mục."""

    def __init__(self, sections: list[Any], slug: str | None = "onboarding") -> None:
        self._queue: list[Any] = [*sections, slug]

    async def scalar(self, _query: object) -> Any:
        return self._queue.pop(0)


class _Llm:
    def __init__(self, reply: Any) -> None:
        self.reply = reply
        self.system_prompts: list[str] = []

    async def complete_json(self, *, system_prompt: str, user_prompt: str, **_: Any) -> str:
        self.system_prompts.append(system_prompt)
        return self.reply if isinstance(self.reply, str) else json.dumps(self.reply)


def _reply(title: str) -> dict[str, Any]:
    return {
        "tasks": [
            {
                "title": title,
                "summary": "Cập nhật nhận diện",
                "steps": ["Cập nhật ảnh đại diện Teams.", "Cài chữ ký email theo mẫu."],
                "done_criteria": ["Xong"],
                "estimated_minutes": 10,
                "sources": [{"section_id": AVATAR.id, "from_line": 1, "to_line": 1}],
                "task_group": "PROFILE",
                "needs": [],
                "warnings": [],
            }
        ],
        "skipped_sections": [],
    }


async def test_a_section_the_ai_skipped_becomes_a_task_when_hr_confirms_it() -> None:
    llm = _Llm(_reply("Cập nhật ảnh đại diện và chữ ký"))

    proposals = await propose_tasks_for_sections(
        _Session([AVATAR]),
        document_version_id=5,
        section_ids=[AVATAR.id],
        llm=llm,
        options=OPTIONS,
    )

    assert [p.title for p in proposals] == ["Cập nhật ảnh đại diện và chữ ký"]
    assert proposals[0].order == 1 and proposals[0].prerequisites == []
    assert proposals[0].source_chunks[0].document_section_id == AVATAR.id
    assert proposals[0].task_group == "PROFILE"
    # Lời nhắc phải nói rõ HR đã xác nhận mục có việc, không để AI lại bỏ qua.
    assert "HR ĐÃ ĐỌC" in llm.system_prompts[0] and "không ghi vào skipped_sections" in llm.system_prompts[0]


async def test_asking_for_a_section_that_is_not_in_the_version_is_a_404() -> None:
    class _Missing(_Session):
        async def scalar(self, _query: object) -> Any:
            return None

    with pytest.raises(PortalError) as raised:
        await propose_tasks_for_sections(
            _Missing([]),
            document_version_id=5,
            section_ids=[999],
            llm=_Llm(_reply("x")),
            options=OPTIONS,
        )
    assert raised.value.code == "SECTION_NOT_FOUND"


async def test_when_the_ai_still_produces_nothing_hr_gets_a_clear_error_not_an_empty_list() -> None:
    with pytest.raises(PortalError) as raised:
        await propose_tasks_for_sections(
            _Session([AVATAR]),
            document_version_id=5,
            section_ids=[AVATAR.id],
            llm=_Llm({"tasks": [], "skipped_sections": [AVATAR.id]}),
            options=OPTIONS,
        )
    assert raised.value.code == "NO_TASK_FROM_SECTION"


async def test_a_task_whose_source_cannot_be_verified_is_dropped() -> None:
    bad = _reply("Việc bịa")
    bad["tasks"][0]["sources"] = [{"section_id": 99999, "from_line": 1, "to_line": 1}]

    with pytest.raises(PortalError) as raised:
        await propose_tasks_for_sections(
            _Session([AVATAR]),
            document_version_id=5,
            section_ids=[AVATAR.id],
            llm=_Llm(bad),
            options=OPTIONS,
        )
    assert raised.value.code == "NO_TASK_FROM_SECTION"


class _Rows:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class _OrderSession:
    def __init__(self, ids: list[int]) -> None:
        self._ids = ids

    async def scalars(self, _query: object) -> _Rows:
        return _Rows(self._ids)


async def test_section_order_returns_ids_in_document_order_and_404_for_an_unknown_version() -> None:
    assert await section_order(_OrderSession([3, 9, 20]), 5) == [3, 9, 20]

    with pytest.raises(PortalError) as raised:
        await section_order(_OrderSession([]), 999)
    assert raised.value.code == "DOCUMENT_VERSION_NOT_FOUND"
