"""Đường nhanh của tạo task bằng AI (kế hoạch tối ưu độ trễ): trích nguồn bằng số dòng, mục "chỉ là thông tin", bù phủ một lượt,
xếp thứ tự có kiểm và quay về thứ tự tài liệu, chia lô song song, báo tiến độ theo bước. Không cần DB: dùng phiên giả và LLM giả."""

import asyncio
import json
from types import SimpleNamespace
from typing import Any

import pytest

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.services.portal.ai_task_service import propose_tasks_detailed
from src.services.portal.errors import PortalError
from src.services.portal.proposal_options import ProposalOptions

FAST = ProposalOptions(mode="fast", batch_words=1000)


class _Rows:
    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def all(self) -> list[Any]:
        return self._items


class _Session:
    def __init__(self, sections: list[Any], slug: str | None = "onboarding") -> None:
        self._sections = sections
        self._slug = slug

    async def scalars(self, _query: object) -> _Rows:
        return _Rows(self._sections)

    async def scalar(self, _query: object) -> str | None:
        return self._slug


def _section(section_id: int, index: int, heading: str, content: str, words: int = 20) -> Any:
    return SimpleNamespace(id=section_id, section_index=index, heading=heading, content=content, token_count=words)


HOSO = _section(
    11, 2, "2. Chuẩn bị hồ sơ", "* CV.\n* Lý lịch tư pháp (bản chính, còn hạn 3 tháng).\n* Căn cước công dân bản gốc."
)
HOPDONG = _section(
    12, 5, "5. Ký hợp đồng", "HR gửi hợp đồng qua email, nhân viên ký và gửi lại trước cuối ngày làm việc."
)
LAPTOP = _section(
    13, 8, "8. Nhận laptop", "Nhận laptop tại tầng 12 và đăng nhập Outlook, Teams trước khi làm việc tiếp theo."
)
INFO = _section(14, 9, "9. Giới thiệu công ty", "Công ty thành lập năm 2010 và có văn phòng ở nhiều thành phố lớn.")


def _task(
    title: str, section: Any, first: int | str = 1, last: int | str | None = None, **extra: Any
) -> dict[str, Any]:
    return {
        "title": title,
        "summary": f"Tóm tắt {title}",
        "steps": [f"Làm {title}."],
        "done_criteria": ["Xong"],
        "estimated_minutes": 10,
        "sources": [{"section_id": section.id, "from_line": first, "to_line": first if last is None else last}],
        "task_group": "PROFILE",
        "needs": [],
        "warnings": [],
        **extra,
    }


class _Recorder:
    """LLM giả ghi lại từng lời gọi (loại, tham số) và trả lời theo kịch bản."""

    def __init__(self, draft: Any, cover: Any = None, order: Any = None) -> None:
        self.draft, self.cover, self.order = draft, cover, order
        self.calls: list[dict[str, Any]] = []

    async def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        timeout_seconds: float | None = None,
        reasoning: bool = True,
        stream: bool = False,
        temperature: float | None = None,
    ) -> str:
        if "sắp xếp các task" in system_prompt:
            kind, script = "order", self.order
        elif "CHƯA CÓ TASK" in system_prompt:
            kind, script = "cover", self.cover
        else:
            kind, script = "draft", self.draft
        self.calls.append(
            {
                "kind": kind,
                "reasoning": reasoning,
                "stream": stream,
                "timeout": timeout_seconds,
                "temperature": temperature,
                "user": user_prompt,
            }
        )
        await asyncio.sleep(0)
        value = script(user_prompt) if callable(script) else script
        if isinstance(value, Exception):
            raise value
        return value if isinstance(value, str) else json.dumps(value if value is not None else {"tasks": []})

    def kinds(self) -> list[str]:
        return [call["kind"] for call in self.calls]


class _Progress:
    def __init__(self) -> None:
        self.events: list[tuple[str, int, int] | tuple[str]] = []

    async def update(self, step: str, *, done: int = 0, total: int = 0) -> None:
        self.events.append((step, done, total))

    async def skip(self, step: str) -> None:
        self.events.append((step,))


async def _run(sections: list[Any], llm: _Recorder, options: ProposalOptions = FAST, progress: Any = None) -> Any:
    return await propose_tasks_detailed(
        _Session(sections),  # type: ignore[arg-type]
        document_version_id=1,
        llm=llm,
        options=options,
        progress=progress,
    )


async def test_fast_path_turns_reasoning_off_streams_and_builds_quote_from_line_numbers() -> None:
    llm = _Recorder({"tasks": [_task("Nộp hồ sơ", HOSO, 2, 3)], "skipped_sections": []})

    result = await _run([HOSO], llm)

    (call,) = llm.calls  # một task thì không cần lời gọi xếp thứ tự
    assert call["reasoning"] is False and call["stream"] is True and call["timeout"] == 60
    assert call["temperature"] == 0.0  # ổn định số task giữa các lần chạy (đo ở ket-qua-13-nhiet-do.json)
    assert "L0: 2. Chuẩn bị hồ sơ" in call["user"] and "L2: * Lý lịch tư pháp" in call["user"]
    (proposal,) = result.proposals
    (chunk,) = proposal.source_chunks
    assert chunk.document_section_id == HOSO.id and chunk.heading == HOSO.heading
    assert "Lý lịch tư pháp" in chunk.quote and "Căn cước công dân" in chunk.quote  # dòng 2 và 3, không có dòng CV
    assert "CV" not in chunk.quote
    assert proposal.instructions_markdown == "Làm Nộp hồ sơ."
    assert proposal.order == 1 and proposal.prerequisites == []
    assert result.order_source == "single"


async def test_line_references_accept_l_prefix_swapped_range_and_clamp_beyond_the_end() -> None:
    llm = _Recorder(
        {
            "tasks": [
                _task("Nộp hồ sơ", HOSO, "L1", "L99"),  # vượt quá số dòng: cắt về dòng cuối
                _task("Ký hợp đồng", HOPDONG, 1, 0),  # ngược thứ tự: tự đổi chỗ
            ]
        },
        order={"order": [1, 2], "prerequisites": {}},
    )

    result = await _run([HOSO, HOPDONG], llm)

    quotes = {p.title: p.source_chunks[0].quote for p in result.proposals}
    assert "Căn cước công dân" in quotes["Nộp hồ sơ"]
    assert "Ký hợp đồng" in quotes["Ký hợp đồng"] and "HR gửi hợp đồng" in quotes["Ký hợp đồng"]


async def test_proposal_with_unknown_section_or_bad_lines_is_dropped() -> None:
    ghost = SimpleNamespace(id=999)
    llm = _Recorder(
        {
            "tasks": [
                _task("Ma", ghost),  # section không thuộc tài liệu
                _task("Dòng sai", HOSO, "abc"),  # không đọc được số dòng
                _task("Dòng ngoài", HOSO, 50, 60),  # bắt đầu sau dòng cuối
                _task("Hợp lệ", HOSO, 1),
            ]
        }
    )

    result = await _run([HOSO], llm)

    assert [p.title for p in result.proposals] == ["Hợp lệ"]


async def test_skipped_sections_are_not_asked_again_and_not_reported_uncovered() -> None:
    llm = _Recorder({"tasks": [_task("Nộp hồ sơ", HOSO)], "skipped_sections": [INFO.id]})

    result = await _run([HOSO, INFO], llm)

    assert llm.kinds() == ["draft"]  # không có lượt bù phủ cho mục chỉ là thông tin
    assert result.uncovered == []
    assert [(item.section_id, item.heading) for item in result.skipped_info] == [
        (INFO.id, INFO.heading)
    ]  # HR vẫn thấy mục bị bỏ qua


async def test_uncovered_section_is_asked_exactly_once_and_listed_if_still_missing() -> None:
    llm = _Recorder(
        {"tasks": [_task("Nộp hồ sơ", HOSO)], "skipped_sections": []},
        cover={"tasks": [], "skipped_sections": []},  # lượt bù vẫn không ra task nào cho mục thông tin
    )

    result = await _run([HOSO, INFO], llm)

    assert llm.kinds() == ["draft", "cover"]  # đúng MỘT lượt bù phủ, không lặp lại
    assert [item.section_id for item in result.uncovered] == [INFO.id]


async def test_coverage_adds_missing_task_and_drops_duplicate_title() -> None:
    llm = _Recorder(
        {"tasks": [_task("Nộp hồ sơ", HOSO)]},
        cover={"tasks": [_task("Nhận laptop", LAPTOP), _task("nộp hồ sơ", HOSO)]},
        order={"order": [1, 2], "prerequisites": {}},
    )

    result = await _run([HOSO, LAPTOP], llm)

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop"]
    assert result.uncovered == []


async def test_ai_order_and_prerequisites_are_applied_only_when_valid() -> None:
    llm = _Recorder(
        {"tasks": [_task("Nộp hồ sơ", HOSO), _task("Ký hợp đồng", HOPDONG), _task("Nhận laptop", LAPTOP)]},
        # Thứ tự dùng số theo thứ tự tài liệu (1 hồ sơ, 2 hợp đồng, 3 laptop). Laptop (3) làm trước hợp đồng (2).
        order={
            "order": [1, 3, 2],
            "prerequisites": {"2": [3, 1, 2, 99, 3], "3": [2], "1": [1]},
        },
    )

    result = await _run([HOSO, HOPDONG, LAPTOP], llm)

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop", "Ký hợp đồng"]
    assert [p.order for p in result.proposals] == [1, 2, 3]
    by_title = {p.title: p.prerequisites for p in result.proposals}
    assert by_title["Ký hợp đồng"] == [
        "Nhận laptop",
        "Nộp hồ sơ",
    ]  # chỉ giữ task đứng trước, bỏ chính nó, số lạ và trùng
    assert by_title["Nhận laptop"] == []  # "3 cần 2" bị bỏ vì 2 nằm SAU 3: không thể tạo vòng
    assert by_title["Nộp hồ sơ"] == []
    assert result.order_source == "ai"


async def test_end_of_day_task_is_forced_last_even_if_ai_puts_it_in_the_middle_and_prerequisites_stay_valid() -> None:
    """Hồi quy: AI xếp việc "cuối ngày" (ký hợp đồng) ở giữa; mã phải đẩy nó ra sau cùng và bỏ tiên quyết trỏ tới nó từ việc đứng trước."""
    llm = _Recorder(
        {"tasks": [_task("Nộp hồ sơ", HOSO), _task("Ký hợp đồng", HOPDONG), _task("Nhận laptop", LAPTOP)]},
        # Số theo thứ tự tài liệu: 1 hồ sơ, 2 hợp đồng (cuối ngày), 3 laptop. AI xếp hợp đồng ở giữa và bắt laptop cần hợp đồng trước.
        order={"order": [1, 2, 3], "prerequisites": {"3": [2, 1], "2": [1]}},
    )

    result = await _run([HOSO, HOPDONG, LAPTOP], llm)

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop", "Ký hợp đồng"]
    by_title = {p.title: p.prerequisites for p in result.proposals}
    assert by_title["Nhận laptop"] == ["Nộp hồ sơ"]  # "cần hợp đồng" bị bỏ vì hợp đồng giờ nằm SAU laptop
    assert by_title["Ký hợp đồng"] == ["Nộp hồ sơ"]
    assert result.order_source == "ai"


@pytest.mark.parametrize(
    "bad_order",
    [
        {"order": [1, 2]},  # thiếu một task
        {"order": [1, 1, 2]},  # trùng
        {"order": [1, 2, 4]},  # ngoài phạm vi
        {"order": "1,2,3"},  # sai kiểu
        {"prerequisites": {}},  # không có order
        "không phải JSON {",
    ],
)
async def test_invalid_order_falls_back_to_document_order_with_end_of_day_last(bad_order: Any) -> None:
    llm = _Recorder(
        {"tasks": [_task("Ký hợp đồng", HOPDONG), _task("Nhận laptop", LAPTOP), _task("Nộp hồ sơ", HOSO)]},
        order=bad_order,
    )

    result = await _run([HOSO, HOPDONG, LAPTOP], llm)

    # Thứ tự tài liệu là hồ sơ (2), hợp đồng (5), laptop (8); việc "cuối ngày" của hợp đồng xếp sau cùng.
    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop", "Ký hợp đồng"]
    assert all(p.prerequisites == [] for p in result.proposals)
    assert result.order_source == "document"


async def test_failed_order_call_falls_back_instead_of_losing_the_tasks() -> None:
    llm = _Recorder(
        {"tasks": [_task("Nộp hồ sơ", HOSO), _task("Nhận laptop", LAPTOP)]},
        order=ChatCompletionError("lỗi mạng khi gọi LLM"),
    )

    result = await _run([HOSO, LAPTOP], llm)

    assert [p.title for p in result.proposals] == ["Nộp hồ sơ", "Nhận laptop"]
    assert result.order_source == "document"


async def test_large_document_is_split_into_parallel_batches_and_each_batch_is_called_once() -> None:
    big = [
        _section(100 + i, i, f"Mục {i}", f"Nội dung mục số {i} cần làm một việc cụ thể.", words=600) for i in range(4)
    ]
    llm = _Recorder(
        lambda user: {"tasks": [_task(f"Việc {i}", s) for i, s in enumerate(big) if f"section_id={s.id} " in user]}
    )

    result = await _run(big, llm, ProposalOptions(mode="fast", batch_words=1000))

    assert llm.kinds().count("draft") == 4 and result.batches == 4  # mỗi lô một mục (600 từ, ngân sách 1000)
    assert len(result.proposals) == 4
    assert all(call["user"].count("section_id=") == 1 for call in llm.calls if call["kind"] == "draft")


async def test_one_failed_batch_is_recovered_by_the_coverage_round() -> None:
    sections = [
        _section(100 + i, i, f"Mục {i}", f"Nội dung mục số {i} cần làm một việc cụ thể.", words=600) for i in range(2)
    ]
    state = {"first": True}

    def draft(user: str) -> Any:
        if f"section_id={sections[1].id} " in user and state["first"]:
            state["first"] = False
            return ChatCompletionError("LLM đang quá tải (429)")
        return {"tasks": [_task(f"Việc {s.id}", s) for s in sections if f"section_id={s.id} " in user]}

    llm = _Recorder(
        draft,
        cover=lambda user: {"tasks": [_task(f"Việc {sections[1].id}", sections[1])]},
        order={"order": [1, 2], "prerequisites": {}},
    )

    result = await _run(sections, llm, ProposalOptions(mode="fast", batch_words=1000))

    assert len(result.proposals) == 2 and result.uncovered == []
    assert llm.kinds().count("cover") == 1


async def test_all_batches_failing_raises_the_real_error() -> None:
    llm = _Recorder(ChatCompletionError("lỗi mạng khi gọi LLM"))

    with pytest.raises(ChatCompletionError):
        await _run([HOSO, LAPTOP], llm)


async def test_invalid_json_everywhere_raises_portal_error() -> None:
    llm = _Recorder("không phải JSON {")

    with pytest.raises(PortalError) as error:
        await _run([HOSO], llm)

    assert error.value.code == "AI_INVALID_JSON"


async def test_progress_reports_real_steps_and_skips_unneeded_ones() -> None:
    progress = _Progress()
    llm = _Recorder({"tasks": [_task("Nộp hồ sơ", HOSO)], "skipped_sections": []})

    await _run([HOSO], llm, progress=progress)

    assert progress.events == [
        ("read", 1, 1),
        ("draft", 0, 1),
        ("draft", 1, 1),
        ("verify", 1, 1),
        ("cover",),  # không còn mục nào chưa có task: bỏ qua bù phủ
        ("order",),  # chỉ một task: không cần xếp thứ tự
    ]


async def test_detail_warning_is_attached_when_source_has_email_not_in_steps() -> None:
    mail = _section(21, 1, "1. Gửi hồ sơ", "Gửi hồ sơ qua email hr@vsf.vn trước thứ Sáu.")
    llm = _Recorder({"tasks": [_task("Gửi hồ sơ", mail)]})

    result = await _run([mail], llm)

    (proposal,) = result.proposals
    assert any("hr@vsf.vn" in note for note in proposal.review_notes)
    assert proposal.confidence == "MEDIUM"


async def test_displayed_quote_of_a_dash_bullet_section_can_be_rechecked_when_hr_creates_the_task() -> None:
    """Hồi quy: docx dùng `- ` làm dấu đầu dòng; quote hiển thị (gộp một dòng) từng không khớp lại ở bước tạo task (422)."""
    from src.services.portal.ai_task_service import section_text
    from src.services.text_match import quote_matches

    docx_like = _section(
        31,
        1,
        "1. Hồ sơ ngày đầu",
        "Chuẩn bị hồ sơ phải nộp:\n- CV.\n- Lý lịch tư pháp.\n- Căn cước công dân bản Photo.\n+ Điểm danh đầu giờ.",
    )
    llm = _Recorder({"tasks": [_task("Nộp hồ sơ", docx_like, 1, 5)]})

    result = await _run([docx_like], llm)

    (proposal,) = result.proposals
    shown = proposal.source_chunks[0].quote
    assert "\n" not in shown and " - CV." in shown
    assert quote_matches(shown, section_text(docx_like))  # đúng phép kiểm của create_task_from_proposal


async def test_empty_steps_lowers_confidence_to_low() -> None:
    llm = _Recorder({"tasks": [_task("Nộp hồ sơ", HOSO, steps=[])]})

    result = await _run([HOSO], llm)

    assert result.proposals[0].confidence == "LOW" and result.proposals[0].instructions_markdown == ""
