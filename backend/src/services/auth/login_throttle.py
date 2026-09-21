"""Giới hạn số lần đăng nhập sai theo khóa (email + IP), đếm trong bộ nhớ của tiến trình.

Giả định đã ghi rõ: MVP chạy **một worker**, nên bộ đếm trong tiến trình là đủ. Khởi động lại thì bộ đếm được xóa, và
nhiều worker sẽ không chia sẻ bộ đếm; khi đó chuyển vào DB (xem plan/phase-4/phase-4.md mục 6).
"""

import math
import time
from collections import deque
from collections.abc import Callable


class LoginThrottle:
    def __init__(
        self,
        max_failures: int,
        window_seconds: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        max_keys: int = 10_000,
    ) -> None:
        self._max_failures = max_failures
        self._window = float(window_seconds)
        self._clock = clock
        self._max_keys = max_keys
        self._failures: dict[str, deque[float]] = {}

    def _recent(self, key: str) -> deque[float]:
        failures = self._failures.get(key)
        if failures is None:
            return deque()
        cutoff = self._clock() - self._window
        while failures and failures[0] <= cutoff:
            failures.popleft()
        if not failures:
            del self._failures[key]
        return failures

    def retry_after(self, key: str) -> int:
        """Số giây phải chờ; 0 nghĩa là được thử."""
        failures = self._recent(key)
        if len(failures) < self._max_failures:
            return 0
        return max(1, math.ceil(failures[0] + self._window - self._clock()))

    def record_failure(self, key: str) -> None:
        self._recent(key)
        if key not in self._failures and len(self._failures) >= self._max_keys:
            self._evict()
        self._failures.setdefault(key, deque()).append(self._clock())

    def reset(self, key: str) -> None:
        self._failures.pop(key, None)

    def _evict(self) -> None:
        """Đầy bộ nhớ: bỏ các khóa đã hết hạn, nếu vẫn đầy thì bỏ khóa cũ nhất (không để kẻ tấn công làm phình bộ nhớ)."""
        for key in list(self._failures):
            self._recent(key)
        if len(self._failures) >= self._max_keys:
            oldest = min(self._failures, key=lambda k: self._failures[k][-1])
            del self._failures[oldest]
