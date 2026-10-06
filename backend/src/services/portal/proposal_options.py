"""Tùy chọn và cổng báo tiến độ cho việc đề xuất task bằng AI (kế hoạch tối ưu độ trễ, Ai-task/ke-hoach-toi-uu-tao-task-bang-ai.md).

Tách thành module nhỏ để `job_service` (giữ `JobContext`) và `ai_task_service` cùng dùng mà không import vòng.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

# Các bước của một lượt tạo task, theo thứ tự (khóa dùng trong `jobs.progress` và giao diện).
STEP_READ = "read"
STEP_DRAFT = "draft"
STEP_VERIFY = "verify"
STEP_COVER = "cover"
STEP_ORDER = "order"
STEP_SAVE = "save"
STEP_KEYS = (STEP_READ, STEP_DRAFT, STEP_VERIFY, STEP_COVER, STEP_ORDER, STEP_SAVE)
# Trọng số phần trăm đo từ thực tế (mục 13 của kế hoạch): bước nào bỏ qua thì phần của nó chia lại cho các bước còn lại.
STEP_WEIGHTS = {STEP_READ: 5, STEP_DRAFT: 65, STEP_VERIFY: 5, STEP_COVER: 10, STEP_ORDER: 10, STEP_SAVE: 5}


@dataclass(frozen=True)
class ProposalOptions:
    """`fast`: tắt suy luận, trích nguồn bằng số dòng, bù phủ một lượt, xếp thứ tự bằng một lời gọi nhỏ.
    `legacy`: cách cũ (suy luận bật, AI chép nguyên văn quote), giữ để so sánh và quay lại khi cần."""

    mode: Literal["fast", "legacy"] = "fast"
    batch_words: int = 2500
    call_timeout_seconds: float = 60


class ProposalProgress(Protocol):
    """Nơi dịch vụ báo "đang ở bước nào, xong bao nhiêu" (chỉ mã bước và số đếm, không nội dung — INV8)."""

    async def update(self, step: str, *, done: int = 0, total: int = 0) -> None: ...

    async def skip(self, step: str) -> None: ...


class NullProgress:
    async def update(self, step: str, *, done: int = 0, total: int = 0) -> None:
        return None

    async def skip(self, step: str) -> None:
        return None
