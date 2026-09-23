"""Theo dõi từng bước xử lý câu hỏi bằng Langfuse (mục 7, kế hoạch 2-C/2-D) — chỉ gửi metadata (độ dài,
thời gian, số lượng, model), **không bao giờ gửi nội dung câu hỏi/câu trả lời thật** (INV8: không đưa dữ
liệu nhạy cảm/nguyên văn ra dịch vụ ngoài).

`LANGFUSE_ENABLED=false` (hoặc chưa cấu hình khóa) -> mọi thao tác là no-op, không gọi mạng, không lỗi.
Lỗi khi gọi Langfuse thật (mạng, khóa sai...) không bao giờ được làm hỏng luồng chat chính — mọi lỗi bị
nuốt và ghi log, không raise ra ngoài.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class _SpanHandle(Protocol):
    def update(self, **fields: Any) -> None: ...


class _NoopSpan:
    def update(self, **fields: Any) -> None:
        pass


class LangfuseTracer:
    def __init__(self, *, enabled: bool, public_key: str | None, secret_key: str | None, host: str | None) -> None:
        self._client: Any = None
        if enabled and public_key and secret_key:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            except Exception:  # SDK lỗi cài đặt/khởi tạo không được chặn luồng chat chính
                logger.warning("Không khởi tạo được Langfuse, tắt theo dõi cho phiên này.", exc_info=True)
                self._client = None

    @contextmanager
    def span(self, name: str, *, metadata: dict[str, Any] | None = None) -> Iterator[_SpanHandle]:
        if self._client is None:
            yield _NoopSpan()
            return

        # Chỉ bọc try/except quanh việc MỞ span thật (lỗi SDK/mạng của Langfuse) — không được bọc quanh
        # `yield`, vì lỗi ném vào từ bên trong khối `with tracer.span(...)` (luồng chat chính) phải được
        # truyền tiếp nguyên vẹn, không bị nuốt hay biến thành "generator didn't stop after throw()".
        try:
            span_cm = self._client.start_as_current_observation(name=name, as_type="span", metadata=metadata)
            span = span_cm.__enter__()
        except Exception:
            logger.warning("Không mở được Langfuse span '%s', bỏ qua theo dõi bước này.", name, exc_info=True)
            yield _NoopSpan()
            return

        try:
            yield span
        except BaseException:
            span_cm.__exit__(*sys.exc_info())
            raise
        else:
            span_cm.__exit__(None, None, None)
