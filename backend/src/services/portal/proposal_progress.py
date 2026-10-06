"""Gom tiến độ tạo task bằng AI của nhiều tài liệu thành MỘT thanh phần trăm và danh sách bước (`jobs.progress`).

Kế hoạch tối ưu độ trễ, mục 13: thanh không còn là đường cong giả theo thời gian mà bám các bước thật (đọc, soạn, kiểm nguồn,
bù phủ, xếp thứ tự, lưu). Trọng số bước đo từ thực tế; bước bị bỏ qua (không cần bù phủ, chỉ có một task nên không cần xếp thứ tự)
thì phần của nó chia lại cho các bước còn lại. Trong lúc chờ một lời gọi LLM, bước đang chạy tiến chậm dần theo thời gian thường
gặp của bước đó để thanh không đứng yên, nhưng không bao giờ chạm 100% trước khi bước thật xong.

Chỉ mã bước, số đếm và thời gian được ghi (INV8: không có nội dung tài liệu).
"""

from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass, field
from typing import Any

from src.services.portal.job_service import JobProgress
from src.services.portal.proposal_options import (
    STEP_COVER,
    STEP_DRAFT,
    STEP_ORDER,
    STEP_READ,
    STEP_SAVE,
    STEP_VERIFY,
    STEP_WEIGHTS,
)

# Phần trăm dành cho bước lưu cuối cùng; các bước theo tài liệu chiếm 0..SAVE_START.
SAVE_START = 100 - STEP_WEIGHTS[STEP_SAVE]
# Thời gian thường gặp (giây) của bước đang chờ LLM, đo ở kế hoạch tối ưu: dùng để làm mượt thanh trong lúc chờ.
EXPECTED_SECONDS = {STEP_READ: 1.0, STEP_DRAFT: 15.0, STEP_VERIFY: 1.0, STEP_COVER: 8.0, STEP_ORDER: 5.0}
DOCUMENT_STEPS = (STEP_READ, STEP_DRAFT, STEP_VERIFY, STEP_COVER, STEP_ORDER)
EASING_CEILING = 0.9  # bước chưa xong thì thanh chỉ tiến tới 90% phần của bước đó
STEP_LABELS = {
    STEP_READ: "Đọc tài liệu",
    STEP_DRAFT: "AI đang soạn task",
    STEP_VERIFY: "Kiểm tra nguồn trích",
    STEP_COVER: "Bù mục còn thiếu",
    STEP_ORDER: "Sắp thứ tự và tiên quyết",
    STEP_SAVE: "Lưu kết quả",
}


@dataclass
class _StepState:
    status: str = "pending"  # pending | running | done | skipped
    done: int = 0
    total: int = 0
    started: float | None = None
    finished: float | None = None


@dataclass
class DocumentSteps:
    """Tiến độ của một tài liệu; đây là đối tượng `ProposalProgress` mà dịch vụ đề xuất gọi."""

    version_id: int
    title: str
    tracker: ProposalTracker
    steps: dict[str, _StepState] = field(default_factory=lambda: {key: _StepState() for key in DOCUMENT_STEPS})
    failed: bool = False
    version_label: str = ""

    async def update(self, step: str, *, done: int = 0, total: int = 0) -> None:
        state = self.steps.get(step)
        if state is None:
            return
        now = time.monotonic()
        state.started = state.started or now
        state.done, state.total = done, total
        if total > 0 and done >= total:
            state.status, state.finished = "done", now
        else:
            state.status = "running"
        await self.tracker.flush()

    async def skip(self, step: str) -> None:
        state = self.steps.get(step)
        if state is not None and state.status != "done":
            state.status = "skipped"
            await self.tracker.flush()

    def finish_all(self) -> None:
        """Tài liệu xong (hoặc hỏng): mọi bước còn dở coi như kết thúc để thanh không kẹt."""
        now = time.monotonic()
        for state in self.steps.values():
            if state.status in ("pending", "running"):
                state.status = "skipped" if state.status == "pending" else "done"
                state.finished = state.finished or now

    def fraction(self, now: float) -> float:
        active = [key for key in DOCUMENT_STEPS if self.steps[key].status != "skipped"]
        total_weight = sum(STEP_WEIGHTS[key] for key in active)
        if total_weight == 0:
            return 1.0
        gained = 0.0
        for key in active:
            state = self.steps[key]
            if state.status == "done":
                part = 1.0
            elif state.status == "running":
                real = state.done / state.total if state.total else 0.0
                eased = (1 - math.exp(-(now - (state.started or now)) / EXPECTED_SECONDS[key])) * EASING_CEILING
                part = min(EASING_CEILING, max(real, eased)) if real < 1 else real
            else:
                part = 0.0
            gained += STEP_WEIGHTS[key] * part
        return gained / total_weight


class ProposalTracker:
    def __init__(self, progress: JobProgress, documents: list[tuple[int, str]]) -> None:
        self._progress = progress
        self._started = time.monotonic()
        self._saving: _StepState | None = None
        self.documents = [DocumentSteps(version_id=v, title=t, tracker=self) for v, t in documents]
        self._lock = asyncio.Lock()

    def snapshot(self) -> tuple[float, str, dict[str, Any]]:
        now = time.monotonic()
        fractions = [1.0 if doc.failed else doc.fraction(now) for doc in self.documents]
        percent = SAVE_START * (sum(fractions) / len(fractions)) if fractions else 0.0
        steps = [self._aggregate(key, now) for key in DOCUMENT_STEPS]
        saving = self._saving
        steps.append(
            {
                "key": STEP_SAVE,
                "status": saving.status if saving else "pending",
                "done": saving.done if saving else 0,
                "total": saving.total if saving else 0,
                "seconds": round((saving.finished or now) - saving.started, 1) if saving and saving.started else None,
            }
        )
        if saving and saving.status == "done":
            percent = 99.0
        elif saving:
            percent = max(percent, SAVE_START)
        running = next((step for step in steps if step["status"] == "running"), None)
        label = STEP_LABELS[running["key"]] if running else "Đang xử lý"
        count = len(self.documents)
        suffix = f" · {count} tài liệu" if count > 1 else ""
        stage = f"{label}{suffix} ({int(now - self._started)} giây)"
        detail = {
            "version": 1,
            "elapsed_seconds": int(now - self._started),
            "steps": steps,
            "documents": [
                {
                    "version_id": doc.version_id,
                    "title": doc.title,
                    "percent": 100 if doc.failed else int(doc.fraction(now) * 100),
                    "failed": doc.failed,
                }
                for doc in self.documents
            ],
        }
        return percent, stage, detail

    def _aggregate(self, key: str, now: float) -> dict[str, Any]:
        states = [doc.steps[key] for doc in self.documents]
        live = [s for s in states if s.status != "skipped"]
        if not live:
            status = "skipped"
        elif all(s.status == "done" for s in live):
            status = "done"
        elif any(s.status in ("running", "done") for s in live):
            status = "running"
        else:
            status = "pending"
        started = [s.started for s in live if s.started is not None]
        seconds: float | None = None
        if started:
            end = max((s.finished or now) for s in live) if status == "done" else now
            seconds = round(end - min(started), 1)
        return {
            "key": key,
            "status": status,
            "done": sum(s.done for s in live),
            "total": sum(s.total for s in live),
            "seconds": seconds,
        }

    async def flush(self) -> None:
        async with self._lock:
            percent, stage, detail = self.snapshot()
            await self._progress.update(percent, stage, detail)

    async def run_ticker(self) -> None:
        """Mỗi giây ghi lại một lần để thanh và đồng hồ chạy đều trong lúc chờ LLM (cũng là nhịp sống của job)."""
        while True:
            await self.flush()
            await asyncio.sleep(1.0)

    async def saving(self) -> None:
        now = time.monotonic()
        self._saving = _StepState(status="running", done=0, total=1, started=now)
        await self.flush()

    async def saved(self) -> None:
        if self._saving is not None:
            self._saving.status, self._saving.done, self._saving.finished = "done", 1, time.monotonic()
        await self.flush()
