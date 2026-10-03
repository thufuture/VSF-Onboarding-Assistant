"""Cổng (Protocol) cho dịch vụ LLM sinh câu trả lời — `DeepSeekChatCompletion` (thật) và
`FakeChatCompletion` (giả, tất định, dùng cho test — không gọi mạng)."""

from __future__ import annotations

from typing import Protocol


class ChatCompletionPort(Protocol):
    async def complete_json(self, *, system_prompt: str, user_prompt: str, timeout_seconds: float | None = None) -> str:
        """Gọi LLM ở chế độ JSON output, trả về chuỗi JSON thô (chưa parse) do LLM sinh ra.

        `timeout_seconds` đặt giới hạn riêng cho lời gọi này (việc dài như soạn cả bộ task); bỏ trống thì dùng mặc định của adapter.
        """
        ...
