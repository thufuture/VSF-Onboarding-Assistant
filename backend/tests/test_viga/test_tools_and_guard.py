"""Công cụ lộ trình, bộ lọc/lối tắt luật và kiểm đầu ra LLM định tuyến của Viga (không cần DB, không gọi mạng)."""

import json
from datetime import UTC, datetime, timedelta

import pytest

from src.services.viga import router, tools
from src.services.viga.guard import is_personal_info_question, normalize_question, shortcut_tool, tool_fits_question
from src.services.viga.snapshot import JourneySnapshot, SnapshotTask

NOW = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def task(
    id: int,
    title: str,
    status: str,
    stage: int = 1,
    stage_title: str = "Ngày 1",
    order: int = 0,
    prereq: tuple[int, ...] = (),
    required: bool = True,
    body: str = "",
) -> SnapshotTask:
    return SnapshotTask(
        id=id,
        title=title,
        status=status,
        stage_id=stage,
        stage_title=stage_title,
        stage_sort=stage,
        sort_order=order,
        required=required,
        body_markdown=body,
        prerequisite_ids=prereq,
    )


def journey(
    *tasks: SnapshotTask, opened: int | None = None, opened_ago: timedelta = timedelta(minutes=5)
) -> JourneySnapshot:
    return JourneySnapshot(
        journey_id=1,
        tasks=tasks,
        last_opened_task_id=opened,
        last_opened_at=NOW - opened_ago if opened else None,
    )


LAPTOP = task(10, "Nhận laptop và đăng nhập", "READY", order=1)
OUTLOOK = task(11, "Cài đặt Outlook", "LOCKED", order=2, prereq=(10,))
AVATAR = task(12, "Ảnh đại diện, chữ ký email", "LOCKED", order=3, prereq=(11,))
TRAIN = task(20, "Tham gia đào tạo hội nhập", "READY", stage=2, stage_title="Ngày 2", order=1)
FULL = journey(LAPTOP, OUTLOOK, AVATAR, TRAIN)


# --- guard ---


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Hôm nay làm gì?", "get_day_plan"),
        ("hôm nay mình cần làm gì", "get_day_plan"),
        ("hom nay lam gi", "get_day_plan"),
        ("Tiếp theo tôi làm gì?", "get_next_tasks"),
        ("Bắt đầu từ đâu?", "get_next_tasks"),
        ("Cho mình hỏi tiến độ của tôi nhé", "get_progress"),
        ("tôi làm được bao nhiêu rồi", "get_progress"),
        ("Nghỉ phép năm bao nhiêu ngày?", None),
        ("task này sao chưa làm được", None),
        ("Hôm nay làm gì và nghỉ phép năm thế nào, cho mình hỏi thêm về bảo hiểm", None),  # câu dài: không ép lối tắt
        ("Nhận laptop xong thì làm gì tiếp theo?", None),  # gắn với một sự kiện trong tài liệu: hỏi đáp tài liệu
        ("Sau khi VinSOC phản hồi email thì làm gì tiếp", None),
        ("Làm gì tiếp", "get_next_tasks"),
        ("Đăng ký faceid xong tôi làm gì tiếp nữa nhỉ hả bạn", None),  # "làm gì tiếp" lọt giữa câu dài
    ],
)
def test_shortcuts_only_fire_on_clear_phrases(question: str, expected: str | None) -> None:
    assert shortcut_tool(question) == expected


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("lương của tôi tháng này là bao nhiêu", True),
        ("Mentor của mình là ai?", True),
        ("chỗ ngồi của em ở đâu", True),
        ("mình còn bao nhiêu ngày phép", True),
        ("mentor cua toi la ai", True),
        # Câu hỏi CHÍNH SÁCH không phải thông tin cá nhân; "tối thiểu" bỏ dấu trùng "tôi" nhưng phải được phân biệt.
        ("lương thử việc tối thiểu bao nhiêu phần trăm", False),
        ("lương tối thiểu vùng là bao nhiêu", False),
        ("Nghỉ phép năm bao nhiêu ngày?", False),
        ("mentor là gì", False),
    ],
)
def test_personal_info_filter_needs_a_first_person_marker(question: str, expected: bool) -> None:
    assert is_personal_info_question(question) is expected


@pytest.mark.parametrize(
    ("tool", "question", "expected"),
    [
        ("get_task_detail", "Hướng dẫn mình việc cài Outlook", True),
        ("get_task_detail", "Tôi nhận laptop ở đâu?", False),
        ("get_task_detail", "Check-in ngày đầu làm thế nào?", True),
        (
            "get_task_detail",
            "T3 chưa trả lời email phê duyệt thì tôi làm sao?",
            False,
        ),  # tình huống: tài liệu mới có đáp án
        ("get_task_detail", "Nếu không có VNeID thì làm thế nào?", False),
        (
            "get_task_detail",
            "Chưa nhận được máy, hướng dẫn mình các bước nhận laptop",
            True,
        ),  # cụm mạnh vẫn mở hướng dẫn
        ("explain_lock", "Vì sao việc này bị khóa?", True),
        ("explain_lock", "Máy tôi đã dùng sẵn Ubuntu thì xin phê duyệt thế nào?", False),
        ("get_next_tasks", "Tiếp theo tôi làm gì?", True),
        ("get_next_tasks", "Nhận laptop xong thì làm gì tiếp theo?", False),
        ("get_day_plan", "Hôm nay có việc gì?", True),
        ("get_progress", "Tiến độ của tôi thế nào", True),
        ("search_documents", "Bất kỳ câu nào", True),
    ],
)
def test_route_tool_must_fit_the_question(tool: str, question: str, expected: bool) -> None:
    assert tool_fits_question(tool, question) is expected


def test_normalization_strips_accents_and_fillers() -> None:
    assert normalize_question("Cho mình hỏi, Hôm nay làm gì nhé?") == "hom nay lam gi"


# --- công cụ lộ trình ---


def test_next_tasks_lists_ready_tasks_required_first_with_open_actions() -> None:
    optional = task(30, "Việc tùy chọn", "READY", order=0, required=False)

    result = tools.get_next_tasks(journey(optional, LAPTOP, OUTLOOK))

    assert result.response_type == "NEXT_STEP"
    assert result.params["title"] == LAPTOP.title  # việc bắt buộc đứng trước việc tùy chọn
    assert [b.task_id for b in result.blocking_tasks] == [10, 30]
    assert result.actions[0] == tools.SuggestedAction("OPEN_TASK", LAPTOP.title, task_id=10)
    assert "Nhận laptop" in result.message


def test_next_tasks_when_everything_is_done() -> None:
    done = journey(task(1, "A", "DONE"), task(2, "B", "DONE"))

    result = tools.get_next_tasks(done)

    assert result.response_type == "INFO"
    assert result.message_key == "allDone"


def test_day_plan_defaults_to_the_first_unfinished_day_and_supports_tomorrow_and_number() -> None:
    today = tools.get_day_plan(FULL)
    tomorrow = tools.get_day_plan(FULL, "tomorrow")
    day_two = tools.get_day_plan(FULL, 2)
    nothing = tools.get_day_plan(FULL, 9)

    assert today.response_type == "DAY_PLAN" and today.params["day"] == "Ngày 1"
    assert today.params["ready"] == 1 and today.params["total"] == 3
    assert tomorrow.params["day"] == "Ngày 2"
    assert day_two.params["day"] == "Ngày 2"
    assert nothing.message_key == "dayNotFound"
    assert {a.type for a in today.actions} == {"OPEN_DAY", "OPEN_TASK"}


def test_explain_lock_names_the_unfinished_prerequisite() -> None:
    result = tools.explain_lock(FULL, AVATAR)

    assert result.response_type == "PREREQUISITE_REQUIRED"
    assert result.params["blocker"] == OUTLOOK.title  # tiên quyết gần nhất chưa xong, không phải mọi việc ở trước
    assert [b.title for b in result.blocking_tasks] == [OUTLOOK.title]
    assert result.actions[0].task_id == OUTLOOK.id


def test_explain_lock_for_ready_done_and_foreign_tasks() -> None:
    assert tools.explain_lock(FULL, LAPTOP).message_key == "taskReady"
    assert tools.explain_lock(FULL, task(10, "Nhận laptop", "DONE")).message_key == "taskDone"
    foreign = tools.explain_lock(FULL, None)
    assert foreign.response_type == "NOT_IN_JOURNEY"
    assert foreign.blocking_tasks == [] and foreign.actions == []  # không lộ gì về việc không thuộc lộ trình


def test_progress_reports_counts_and_percent() -> None:
    result = tools.get_progress(journey(task(1, "A", "DONE"), task(2, "B", "READY"), task(3, "C", "LOCKED")))

    assert (result.params["done"], result.params["total"], result.params["percent"]) == (1, 3, 33)


def test_task_detail_truncates_long_instructions() -> None:
    long = task(5, "Việc dài", "READY", body="Bước một. " * 200)

    result = tools.get_task_detail(long)

    assert result.response_type == "INFO"
    assert len(str(result.params["detail"])) <= tools.DETAIL_MAX_CHARS + 1


# --- xác định "việc nào" (15.3d, 15.3e) ---


def test_task_resolution_priority_explicit_then_name_then_last_opened_then_first_ready() -> None:
    snapshot = journey(LAPTOP, OUTLOOK, AVATAR, TRAIN, opened=AVATAR.id)

    explicit = tools.resolve_task(snapshot, "task này sao chưa làm được", OUTLOOK.id, NOW)
    by_name = tools.resolve_task(snapshot, "sao chưa làm được task nhận laptop", None, NOW)
    last_opened = tools.resolve_task(snapshot, "task này sao chưa làm được", None, NOW)
    first_ready = tools.resolve_task(journey(LAPTOP, OUTLOOK, AVATAR, TRAIN), "task này sao chưa làm được", None, NOW)

    assert explicit.task == OUTLOOK
    assert by_name.task == LAPTOP  # nêu tên thì ưu tiên hơn việc vừa mở
    assert last_opened.task == AVATAR and not last_opened.assumed
    assert first_ready.task == LAPTOP and first_ready.assumed  # phải nói rõ giả định


def test_last_opened_task_expires_after_thirty_minutes() -> None:
    stale = journey(LAPTOP, OUTLOOK, AVATAR, opened=AVATAR.id, opened_ago=timedelta(minutes=31))

    resolution = tools.resolve_task(stale, "task này sao chưa làm được", None, NOW)

    assert resolution.task == LAPTOP and resolution.assumed


def test_ordinal_reference_uses_the_current_day_order() -> None:
    assert tools.resolve_task(FULL, "việc số 2 làm thế nào", None, NOW).task == OUTLOOK
    assert tools.resolve_task(FULL, "task 03", None, NOW).task == AVATAR
    assert tools.task_by_ordinal(FULL, "việc số 9") is None


def test_ambiguous_name_asks_instead_of_guessing() -> None:
    one = task(1, "Đăng ký tủ gửi đồ", "READY", order=1)
    two = task(2, "Đăng ký tủ để giày", "READY", order=2)
    snapshot = journey(one, two)

    reply = tools.run_task_tool("explain_lock", snapshot, "đăng ký tủ", None, NOW)

    assert reply.response_type == "CLARIFY"
    assert {a.task_id for a in reply.actions} == {1, 2}


def test_run_task_tool_says_which_task_it_assumed() -> None:
    reply = tools.run_task_tool("explain_lock", FULL, "task này sao chưa làm được", None, NOW)

    assert reply.assumed_title == LAPTOP.title
    assert reply.message_key == "taskReady"


def test_explicit_id_outside_the_journey_is_not_in_journey_and_leaks_nothing() -> None:
    reply = tools.run_task_tool("get_task_detail", FULL, "việc này", 99999, NOW)

    assert reply.response_type == "NOT_IN_JOURNEY"
    assert reply.params == {}


def test_llm_view_has_only_ids_titles_status_and_day() -> None:
    view = FULL.llm_view()

    assert "id=10 | Nhận laptop và đăng nhập | READY | Ngày 1" in view
    assert "@" not in view  # không có email, tên hay phòng ban của nhân viên


# --- kiểm đầu ra LLM định tuyến ---


def raw(**fields: object) -> str:
    return json.dumps(fields, ensure_ascii=False)


def test_route_accepts_a_valid_tool_choice() -> None:
    decision = router.parse_route(raw(tool="explain_lock", args={"task_id": 12}, confidence=0.9, clarify=None), FULL)

    assert decision is not None
    assert (decision.tool, decision.args, decision.confidence) == ("explain_lock", {"task_id": 12}, 0.9)


@pytest.mark.parametrize(
    "payload",
    [
        "không phải json",
        json.dumps(["tool"]),
        raw(tool="delete_everything", args={}, confidence=0.9),  # công cụ ngoài danh sách đóng
        raw(tool="get_progress", args={}, confidence=1.5),  # confidence ngoài [0, 1]
        raw(tool="get_progress", args={}),  # thiếu confidence
        raw(tool="get_progress", args={}, confidence=True),
    ],
)
def test_route_rejects_anything_outside_the_closed_schema(payload: str) -> None:
    assert router.parse_route(payload, FULL) is None


def test_route_never_trusts_a_task_id_outside_the_journey() -> None:
    decision = router.parse_route(raw(tool="get_task_detail", args={"task_id": 99999}, confidence=0.95), FULL)

    assert decision is not None
    assert decision.unknown_task is True
    assert "task_id" not in decision.args  # mã bịa hoặc của người khác không được dùng


def test_route_cleans_day_and_query_arguments() -> None:
    day = router.parse_route(raw(tool="get_day_plan", args={"day": "yesterday"}, confidence=0.8), FULL)
    search = router.parse_route(raw(tool="search_documents", args={"query": "  nghỉ phép năm  "}, confidence=0.8), FULL)

    assert day is not None and day.args == {"day": None}
    assert search is not None and search.args == {"query": "nghỉ phép năm"}


def test_route_prompt_has_no_personal_data_and_wraps_the_question() -> None:
    prompt = router.build_prompt(
        "Cho mình hỏi", FULL, [("USER", "hôm nay làm gì"), ("ASSISTANT", "Bạn làm Nhận laptop")]
    )

    assert "<journey>" in prompt and "<history>" in prompt
    assert "<user_input>Cho mình hỏi</user_input>" in prompt
    assert "@" not in prompt  # không có email


def test_every_exit_template_exists_for_each_response_key() -> None:
    for key in ("noBasis", "outOfScope", "assistantUnavailable", "smalltalk", "clarifyTask", "noJourney"):
        assert tools.render(key)


def test_parse_route_reads_none_kind() -> None:
    from src.services.viga.router import parse_route

    decision = parse_route(
        '{"tool": "none", "args": {}, "confidence": 0.9, "clarify": null, "kind": "out_of_scope"}', None
    )

    assert decision is not None and decision.kind == "out_of_scope"


def test_parse_route_ignores_kind_for_other_tools_and_bad_values() -> None:
    from src.services.viga.router import parse_route

    with_tool = parse_route('{"tool": "get_progress", "args": {}, "confidence": 0.9, "kind": "injection"}', None)
    bad_kind = parse_route('{"tool": "none", "args": {}, "confidence": 0.9, "kind": "weird"}', None)

    assert with_tool is not None and with_tool.kind is None
    assert bad_kind is not None and bad_kind.kind is None
