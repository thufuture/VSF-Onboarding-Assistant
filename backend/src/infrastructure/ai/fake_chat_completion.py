"""LLM giả, tất định — dùng cho test (không gọi mạng, không tốn tiền). Trả JSON đã cấu hình sẵn theo
từ khóa xuất hiện trong `user_prompt`, hoặc một hàm tùy biến hoàn toàn cho từng test.
"""

from __future__ import annotations

from collections.abc import Callable

FixedResponse = str | Callable[[str, str], str]


class FakeChatCompletion:
    def __init__(self, response: FixedResponse) -> None:
        self._response = response

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
        if callable(self._response):
            return self._response(system_prompt, user_prompt)
        return self._response
