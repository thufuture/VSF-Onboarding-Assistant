"""Lớp bọc dự phòng cho LLM: khi nhà cung cấp chính lỗi hạ tầng thì chuyển sang nhà cung cấp thứ hai (mặc định Claude Haiku).

Quy tắc (xem docs/value/optimize-chatviga/bao-cao-trien-khai-viga.md):
- Chỉ chuyển khi nhà cung cấp chính đã thử lại xong mà vẫn lỗi hạ tầng: hết giờ, mạng, 429, 5xx, hoặc từ chối xác thực (khóa hỏng).
  Lỗi nội dung (phản hồi sai định dạng) KHÔNG chuyển, vì mô hình khác không sửa được và chỉ tốn tiền.
- Bộ ngắt mạch: sau `failure_threshold` lỗi liên tiếp thì bỏ qua nhà cung cấp chính trong `cooldown_seconds`, để mỗi câu hỏi không phải
  chờ hết giờ rồi mới sang dự phòng. Hết thời gian nghỉ thì thử lại nhà cung cấp chính; thành công thì đóng bộ ngắt.
- Việc nền (sinh task bằng AI) chỉ dùng dự phòng khi `allow_background=True`.
- Bộ ngắt mạch phải dùng chung giữa các lời gọi: người dựng lớp bọc giữ một `CircuitBreaker` lâu dài, không tạo mới mỗi yêu cầu.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.ai.deepseek_adapter import ChatCompletionError
from src.infrastructure.observability.call_metrics import current_job_id

logger = logging.getLogger(__name__)

# Mã lỗi hạ tầng đáng chuyển sang nhà cung cấp dự phòng.
FALLBACK_CODES = frozenset({"timeout", "network", "rate_limited", "http_error", "auth"})


class CircuitBreaker:
    def __init__(
        self, *, failure_threshold: int = 3, cooldown_seconds: float = 60.0, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._threshold = failure_threshold
        self._cooldown = cooldown_seconds
        self._clock = clock
        self._failures = 0
        self._open_until = 0.0

    @property
    def is_open(self) -> bool:
        return self._clock() < self._open_until

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._open_until = self._clock() + self._cooldown
            self._failures = 0

    def record_success(self) -> None:
        self._failures = 0
        self._open_until = 0.0


class FallbackChatCompletion:
    def __init__(
        self,
        primary: ChatCompletionPort,
        secondary: ChatCompletionPort,
        breaker: CircuitBreaker,
        *,
        allow_background: bool = False,
    ) -> None:
        self._primary = primary
        self._secondary = secondary
        self._breaker = breaker
        self._allow_background = allow_background

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
        arguments: dict[str, Any] = {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "timeout_seconds": timeout_seconds,
            "reasoning": reasoning,
            "stream": stream,
            "temperature": temperature,
        }
        can_fall_back = self._allow_background or current_job_id() is None
        if can_fall_back and self._breaker.is_open:
            return await self._secondary.complete_json(**arguments)
        try:
            result = await self._primary.complete_json(**arguments)
        except ChatCompletionError as exc:
            if not can_fall_back or exc.code not in FALLBACK_CODES:
                raise
            self._breaker.record_failure()
            logger.warning("llm_fallback_used primary_error=%s", exc.code)
            return await self._secondary.complete_json(**arguments)
        self._breaker.record_success()
        return result
