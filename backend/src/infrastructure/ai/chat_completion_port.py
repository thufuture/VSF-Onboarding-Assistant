"""Cổng (Protocol) cho dịch vụ LLM sinh câu trả lời — `DeepSeekChatCompletion` (thật) và
`FakeChatCompletion` (giả, tất định, dùng cho test — không gọi mạng)."""

from __future__ import annotations

from typing import Protocol


class ChatCompletionPort(Protocol):
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
        """Gọi LLM ở chế độ JSON output, trả về chuỗi JSON thô (chưa parse) do LLM sinh ra.

        `timeout_seconds` đặt giới hạn riêng cho lời gọi này (việc dài như soạn cả bộ task); bỏ trống thì dùng mặc định của adapter.
        `reasoning=False` tắt bước suy luận ẩn của model (nhanh hơn nhiều với việc soạn có khuôn mẫu rõ, chất lượng đã đo ở
        `Ai-task/ke-hoach-toi-uu-tao-task-bang-ai.md`); mặc định giữ hành vi cũ. `stream=True` đọc theo từng đoạn để ghi số đo
        từng pha và có timeout "im lặng"; kết quả trả về vẫn là toàn bộ chuỗi JSON. `temperature=0` làm kết quả ổn định hơn giữa các lần
        gọi (đo thật ở `thu-nghiem/ket-qua-13-nhiet-do.json`); bỏ trống thì dùng mặc định của nhà cung cấp.
        """
        ...
