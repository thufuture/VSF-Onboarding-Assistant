"""Giữ dịch vụ embedding (Modal, GPU) ấm khi đang có người dùng, để lần hỏi đầu tiên không phải đợi khởi động nguội (~20 giây).

Modal tự tắt container khi không có ai gọi một lúc. Thay vì giữ GPU chạy cả ngày (tốn tiền), backend:
- đánh thức ngay khi có người đăng nhập (chạy nền, người dùng không phải đợi);
- trong `window_seconds` kể từ hoạt động cuối (đăng nhập, hỏi Viga/chat), cứ mỗi `interval` giây gọi một lần embedding rất nhỏ.
Hết hoạt động thì dừng gọi và Modal tự tắt. Lỗi mạng chỉ ghi log, không ảnh hưởng ai.
"""

from __future__ import annotations

import asyncio
import logging
import time

from src.infrastructure.observability.call_metrics import call_context
from src.services.ingest.embedding.port import EmbeddingPort

logger = logging.getLogger(__name__)

PING_TEXT = "khởi động"


class KeepWarm:
    def __init__(self, embedding: EmbeddingPort, *, window_seconds: float) -> None:
        self._embedding = embedding
        self._window = window_seconds
        self._last_activity: float | None = None
        self._pinging = False
        self._tasks: set[asyncio.Task[None]] = set()

    def touch(self) -> None:
        """Ghi nhận có người đang dùng (đăng nhập, đặt câu hỏi)."""
        self._last_activity = time.monotonic()

    def wake(self) -> None:
        """Đánh thức dịch vụ ngay trong nền (không chờ kết quả)."""
        self.touch()
        task = asyncio.create_task(self.ping())
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    def active(self) -> bool:
        return self._last_activity is not None and time.monotonic() - self._last_activity < self._window

    async def ping(self) -> None:
        if self._pinging:  # đang có một lần gọi (có thể đang khởi động nguội): không xếp chồng
            return
        self._pinging = True
        try:
            with call_context(operation="ingest.probe"):
                await self._embedding.embed([PING_TEXT])
        except Exception:
            logger.warning("embedding_keep_warm_failed", exc_info=True)
        finally:
            self._pinging = False

    async def tick(self) -> None:
        """Việc định kỳ: chỉ gọi khi gần đây có hoạt động."""
        if self.active():
            await self.ping()
