"""Bộ giới hạn số lời gọi LLM chạy cùng lúc (kế hoạch tối ưu tạo task bằng AI, mục 8.4).

Nhà cung cấp chỉ cho một số lời gọi song song mỗi tài khoản (đo thật: 11, vượt thì HTTP 429), và con số đó dùng chung cho
Viga (người dùng đang chờ) lẫn việc nền (tạo task bằng AI). Hai tầng:
- tổng số lời gọi cùng lúc (`total`, mặc định 9 — chừa chỗ dự phòng dưới mức 11);
- riêng việc nền (`background`, mặc định 5) để một lượt tạo task nhiều nhóm không chiếm hết chỗ của Viga.

Việc nền lấy chỗ nền trước rồi mới lấy chỗ chung, nên khi đã đủ 5 việc nền thì việc thứ 6 xếp hàng mà không giữ chỗ chung.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager


class LlmGate:
    def __init__(self, total: int, background: int) -> None:
        if total < 1 or background < 1:
            raise ValueError("giới hạn đồng thời phải ≥ 1")
        self.total = total
        self.background = min(background, total)
        self._total = asyncio.Semaphore(total)
        self._background = asyncio.Semaphore(self.background)
        self.in_flight = 0
        self.peak = 0

    @asynccontextmanager
    async def slot(self, *, background: bool) -> AsyncIterator[float]:
        """Giữ một chỗ trong lúc gọi LLM; trả về số mili-giây đã chờ để có chỗ (đưa vào `llm_calls.queue_wait_ms`)."""
        waited_from = time.perf_counter()
        if background:
            await self._background.acquire()
        try:
            await self._total.acquire()
        except BaseException:
            if background:
                self._background.release()
            raise
        self.in_flight += 1
        self.peak = max(self.peak, self.in_flight)
        try:
            yield (time.perf_counter() - waited_from) * 1000
        finally:
            self.in_flight -= 1
            self._total.release()
            if background:
                self._background.release()


_shared: LlmGate | None = None


def shared_gate(total: int, background: int) -> LlmGate:
    """Một bộ giới hạn dùng chung cho cả tiến trình (adapter được dựng mới mỗi request nhưng chỗ trống thì chung)."""
    global _shared
    if _shared is None:
        _shared = LlmGate(total, background)
    return _shared


def reset_shared_gate() -> None:
    """Chỉ dùng trong test."""
    global _shared
    _shared = None
