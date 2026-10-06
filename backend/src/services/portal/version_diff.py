"""So sánh hai tập việc theo `origin_key`: nguồn của "trước và sau" ở hộp xem trước áp dụng và ở thông báo cho nhân viên.

Hàm THUẦN (không đụng DB) để dễ kiểm thử. Hai phía được đưa về cùng dạng `TaskView`:
- phía mẫu: các việc của một phiên bản của một ngày (`task_templates` + `task_dependencies`);
- phía nhân viên: các việc trong bản sao của người đó (`employee_tasks` + `employee_task_dependencies`).
Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md mục 4.5.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.model.enums import ChangeKind

# Các trường được so sánh và hiển thị "trước và sau". `sort_order` KHÔNG nằm đây: chèn một việc vào giữa làm số thứ tự của
# mọi việc sau nó đổi theo, sẽ sinh thông báo thừa. Thứ tự vẫn được cập nhật khi nhân viên bấm "Cập nhật" một việc.
CONTENT_FIELDS = ("title", "body_markdown", "required", "task_group")


@dataclass(frozen=True)
class TaskView:
    origin_key: UUID
    title: str
    body_markdown: str
    required: bool
    task_group: str | None
    sort_order: int
    prerequisite_keys: tuple[UUID, ...] = ()
    # Chỉ có ở phía nhân viên:
    employee_task_id: int | None = None
    status: str | None = None
    # Chỉ có ở phía mẫu (để việc sao chép về sau giữ được nguồn trích dẫn):
    source_task_template_id: int | None = None


@dataclass
class TaskChange:
    kind: ChangeKind
    origin_key: UUID
    title: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    employee_task_id: int | None = None
    employee_status: str | None = None
    # Việc đã làm bị bỏ ở bản mới: giữ nguyên, chỉ báo thông tin (không có nút cho nhân viên).
    informational: bool = False
    notes: list[str] = field(default_factory=list)


def snapshot(task: TaskView, titles: dict[UUID, str]) -> dict[str, Any]:
    """Nội dung của một việc dưới dạng JSON để lưu vào thông báo (không chứa dữ liệu cá nhân)."""
    return {
        "title": task.title,
        "body_markdown": task.body_markdown,
        "required": task.required,
        "task_group": task.task_group,
        "sort_order": task.sort_order,
        "prerequisites": [titles.get(key, "") for key in task.prerequisite_keys],
        "prerequisite_keys": [str(key) for key in task.prerequisite_keys],
        "source_task_template_id": task.source_task_template_id,
    }


def _differs(current: TaskView, target: TaskView) -> bool:
    return any(getattr(current, name) != getattr(target, name) for name in CONTENT_FIELDS)


def diff_tasks(current: Sequence[TaskView], target: Sequence[TaskView]) -> list[TaskChange]:
    """Thay đổi để đưa `current` thành `target`, sắp theo thứ tự của `target` (việc bị bỏ xếp cuối)."""
    by_key = {task.origin_key: task for task in current}
    target_keys = {task.origin_key for task in target}
    current_titles = {task.origin_key: task.title for task in current}
    target_titles = {task.origin_key: task.title for task in target}
    changes: list[TaskChange] = []

    for task in sorted(target, key=lambda item: (item.sort_order, str(item.origin_key))):
        existing = by_key.get(task.origin_key)
        if existing is None:
            changes.append(
                TaskChange(
                    kind=ChangeKind.ADDED,
                    origin_key=task.origin_key,
                    title=task.title,
                    before=None,
                    after=snapshot(task, target_titles),
                )
            )
            continue
        content_changed = _differs(existing, task)
        # So tiên quyết theo mã việc (tên có thể đổi), chỉ tính tiên quyết còn tồn tại ở cả hai phía.
        before_keys = {key for key in existing.prerequisite_keys if key in by_key}
        after_keys = set(task.prerequisite_keys)
        prerequisites_changed = before_keys != after_keys
        if not content_changed and not prerequisites_changed:
            continue
        changes.append(
            TaskChange(
                kind=ChangeKind.MODIFIED if content_changed else ChangeKind.PREREQUISITES,
                origin_key=task.origin_key,
                title=task.title,
                before=snapshot(existing, current_titles),
                after=snapshot(task, target_titles),
                employee_task_id=existing.employee_task_id,
                employee_status=existing.status,
            )
        )

    for task in sorted(current, key=lambda item: (item.sort_order, str(item.origin_key))):
        if task.origin_key in target_keys:
            continue
        done = task.status == "DONE"
        changes.append(
            TaskChange(
                kind=ChangeKind.REMOVED,
                origin_key=task.origin_key,
                title=task.title,
                before=snapshot(task, current_titles),
                after=None,
                employee_task_id=task.employee_task_id,
                employee_status=task.status,
                informational=done,
            )
        )
    return changes


def summarize(changes: Sequence[TaskChange]) -> dict[str, int]:
    """Số việc đổi, thêm, bỏ (cho hộp xem trước của HR)."""
    return {
        "modified": sum(1 for c in changes if c.kind in (ChangeKind.MODIFIED, ChangeKind.PREREQUISITES)),
        "added": sum(1 for c in changes if c.kind == ChangeKind.ADDED),
        "removed": sum(1 for c in changes if c.kind == ChangeKind.REMOVED),
    }


def changed_fields(change: TaskChange) -> list[str]:
    """Tên các trường đã đổi (để thông báo ghi "Nội dung và hạn nộp đã đổi" mà không phải so lại ở giao diện)."""
    if change.before is None or change.after is None:
        return []
    names = [name for name in CONTENT_FIELDS if change.before.get(name) != change.after.get(name)]
    if change.before.get("prerequisite_keys") != change.after.get("prerequisite_keys"):
        names.append("prerequisites")
    return names
