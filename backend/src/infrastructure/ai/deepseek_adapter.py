"""Adapter gọi DeepSeek qua giao diện tương thích OpenAI (`POST /chat/completions`,
`response_format: {"type": "json_object"}`). Đã gọi thử thật trước khi viết adapter (bắt buộc theo
master-plan): model `deepseek-flash` trả `200`, hỗ trợ JSON mode; trường `reasoning_content` (suy luận
nội bộ) bị bỏ qua, chỉ lấy `content` (JSON cuối cùng).
"""

from __future__ import annotations

import httpx


class ChatCompletionError(Exception):
    """Lỗi khi gọi LLM — người gọi phải coi như "chưa có căn cứ", không hiển thị câu trả lời chưa kiểm chứng."""


class DeepSeekChatCompletion:
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout_seconds: float = 60) -> None:
        if not base_url or not api_key or not model:
            raise ValueError("cần LLM_BASE_URL, LLM_API_KEY, LLM_MODEL")
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds

    async def complete_json(self, *, system_prompt: str, user_prompt: str) -> str:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json={
                        "model": self._model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "response_format": {"type": "json_object"},
                    },
                    timeout=self._timeout,
                )
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                raise ChatCompletionError(f"lỗi mạng khi gọi LLM: {exc}") from exc
        if response.status_code in (401, 403):
            raise ChatCompletionError(f"LLM từ chối xác thực ({response.status_code}) — kiểm tra LLM_API_KEY")
        if response.status_code != 200:
            raise ChatCompletionError(f"LLM lỗi: {response.status_code} {response.text[:200]}")
        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError) as exc:
            raise ChatCompletionError(f"phản hồi LLM sai định dạng: {exc}") from exc
