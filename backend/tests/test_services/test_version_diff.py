"""So sánh hai tập việc theo `origin_key` (hàm thuần): nguồn của "trước và sau" khi áp dụng một phiên bản mới."""

from uuid import UUID, uuid4

from src.model.enums import ChangeKind
from src.services.portal.version_diff import TaskView, changed_fields, diff_tasks, summarize

A, B, C, D = (uuid4() for _ in range(4))


def task(
    key: UUID,
    title: str,
    *,
    body: str = "nội dung",
    sort: int = 1,
    prerequisites: tuple[UUID, ...] = (),
    **extra: object,
) -> TaskView:
    return TaskView(
        origin_key=key,
        title=title,
        body_markdown=body,
        required=bool(extra.get("required", True)),
        task_group=extra.get("task_group"),  # type: ignore[arg-type]
        sort_order=sort,
        prerequisite_keys=prerequisites,
        employee_task_id=int(extra["employee_task_id"]) if "employee_task_id" in extra else None,  # type: ignore[call-overload]
        status=str(extra["status"]) if "status" in extra else None,
    )


def test_identical_sets_have_no_changes() -> None:
    tasks = [task(A, "A"), task(B, "B", sort=2, prerequisites=(A,))]

    assert diff_tasks(tasks, list(tasks)) == []


def test_reordering_only_is_not_a_change() -> None:
    """Chèn một việc vào giữa làm số thứ tự mọi việc sau nó đổi theo: không được sinh thông báo thừa."""
    before = [task(A, "A", sort=1), task(B, "B", sort=2)]
    after = [task(A, "A", sort=1), task(B, "B", sort=5)]

    assert diff_tasks(before, after) == []


def test_modified_added_and_removed_are_detected_in_order() -> None:
    before = [task(A, "A", body="cũ", sort=1), task(B, "B", sort=2), task(C, "C", sort=3)]
    after = [task(A, "A", body="mới", sort=1), task(B, "B", sort=2), task(D, "D", sort=3)]

    changes = diff_tasks(before, after)

    assert [(c.kind, c.title) for c in changes] == [
        (ChangeKind.MODIFIED, "A"),
        (ChangeKind.ADDED, "D"),
        (ChangeKind.REMOVED, "C"),
    ]
    modified = changes[0]
    assert modified.before is not None and modified.after is not None
    assert modified.before["body_markdown"] == "cũ" and modified.after["body_markdown"] == "mới"
    assert changed_fields(modified) == ["body_markdown"]
    assert summarize(changes) == {"modified": 1, "added": 1, "removed": 1}


def test_renaming_keeps_the_same_task_because_matching_is_by_origin_key() -> None:
    changes = diff_tasks([task(A, "Tên cũ")], [task(A, "Tên mới")])

    assert [(c.kind, c.title) for c in changes] == [(ChangeKind.MODIFIED, "Tên mới")]
    assert changed_fields(changes[0]) == ["title"]


def test_only_prerequisites_changed_is_its_own_kind_and_compares_by_key_not_by_title() -> None:
    before = [task(A, "A"), task(B, "B", sort=2), task(C, "C", sort=3, prerequisites=(A,))]
    after = [task(A, "A"), task(B, "B", sort=2), task(C, "C", sort=3, prerequisites=(A, B))]

    changes = diff_tasks(before, after)

    assert [(c.kind, c.title) for c in changes] == [(ChangeKind.PREREQUISITES, "C")]
    assert changed_fields(changes[0]) == ["prerequisites"]
    assert changes[0].after is not None and changes[0].after["prerequisites"] == ["A", "B"]


def test_a_prerequisite_that_does_not_exist_in_the_employees_copy_is_ignored_when_comparing() -> None:
    """Tiên quyết trỏ tới việc đã bị bỏ khỏi bản sao của nhân viên không được tính là "đã đổi" mãi mãi."""
    before = [task(C, "C", prerequisites=(D,))]  # D không còn trong bản sao
    after = [task(C, "C")]

    assert diff_tasks(before, after) == []


def test_removed_done_task_is_informational_and_removed_open_task_is_not() -> None:
    before = [
        task(A, "A đã xong", employee_task_id=1, status="DONE"),
        task(B, "B chưa làm", sort=2, employee_task_id=2, status="READY"),
    ]

    changes = {c.title: c for c in diff_tasks(before, [])}

    assert changes["A đã xong"].informational is True  # việc đã làm giữ nguyên, chỉ báo thông tin
    assert changes["B chưa làm"].informational is False
    assert changes["B chưa làm"].employee_status == "READY"


def test_employee_status_and_task_id_travel_with_the_change() -> None:
    before = [task(A, "A", body="cũ", employee_task_id=7, status="DONE")]
    after = [task(A, "A", body="mới")]

    (change,) = diff_tasks(before, after)

    assert (change.employee_task_id, change.employee_status) == (7, "DONE")
