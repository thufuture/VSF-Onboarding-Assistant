"""Giới hạn số câu hỏi `/api/v1/chat/ask` theo `user_id`, trong một cửa sổ thời gian.

Tái dùng nguyên `LoginThrottle` (đếm trong bộ nhớ của tiến trình, đủ cho MVP một worker — cùng giả định đã
ghi trong `login_throttle.py`), chỉ đổi ngữ nghĩa: không phải "số lần sai" mà "số lần gọi". Xem
docs/chatbot-vsf/plan/phase-2/2-e-prompt-guardrail-rerank/03-generation-guardrail-tien-kiem.md mục 4.4.
"""

from __future__ import annotations

from src.services.auth.login_throttle import LoginThrottle


class ChatThrottle:
    def __init__(self, max_questions: int, window_seconds: int) -> None:
        self._counter = LoginThrottle(max_questions, window_seconds)

    def retry_after(self, user_id: int) -> int:
        """Số giây phải chờ trước khi được hỏi tiếp; 0 nghĩa là được hỏi ngay."""
        return self._counter.retry_after(str(user_id))

    def record_question(self, user_id: int) -> None:
        self._counter.record_failure(str(user_id))
