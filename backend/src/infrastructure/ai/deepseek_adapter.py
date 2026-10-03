"""Adapter gọi DeepSeek qua giao diện tương thích OpenAI (`POST /chat/completions`,
`response_format: {"type": "json_object"}`). Đã gọi thử thật trước khi viết adapter (bắt buộc theo
master-plan): model `deepseek-flash` trả `200`, hỗ trợ JSON mode; trường `reasoning_content` (suy luận
nội bộ) bị bỏ qua, chỉ lấy `content` (JSON cuối cùng).
"""

from __future__ import annotations

import time

import httpx

from src.infrastructure.observability.call_metrics import CallRecord, emit


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

    async def complete_json(self, *, system_prompt: str, user_prompt: str, timeout_seconds: float | None = None) -> str:
        started = time.perf_counter()
        try:
            return await self._complete_json(system_prompt, user_prompt, started, timeout_seconds or self._timeout)
        except ChatCompletionError as exc:
            self._emit(started, ok=False, error=_error_code(exc))
            raise

    def _emit(
        self, started: float, *, ok: bool, prompt_tokens: int = 0, completion_tokens: int = 0, error: str | None = None
    ) -> None:
        emit(
            CallRecord(
                kind="llm",
                provider="deepseek",
                model=self._model,
                latency_ms=(time.perf_counter() - started) * 1000,
                ok=ok,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                error=error,
            )
        )

    async def _complete_json(self, system_prompt: str, user_prompt: str, started: float, timeout: float) -> str:
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
                    timeout=timeout,
                )
            except (httpx.TimeoutException, httpx.ConnectError, httpx.NetworkError) as exc:
                raise ChatCompletionError(f"lỗi mạng khi gọi LLM: {exc}") from exc
        if response.status_code in (401, 403):
            raise ChatCompletionError(f"LLM từ chối xác thực ({response.status_code}) — kiểm tra LLM_API_KEY")
        if response.status_code != 200:
            raise ChatCompletionError(f"LLM lỗi: {response.status_code} {response.text[:200]}")
        try:
            data = response.json()
            content = str(data["choices"][0]["message"]["content"])
        except (ValueError, KeyError, IndexError) as exc:
            raise ChatCompletionError(f"phản hồi LLM sai định dạng: {exc}") from exc
        usage = data.get("usage") if isinstance(data, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        self._emit(
            started,
            ok=True,
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
        )
        return content


def _error_code(exc: ChatCompletionError) -> str:
    """Mã lỗi ngắn để thống kê (không chứa nội dung); phần chi tiết đã nằm trong thông điệp ngoại lệ."""
    message = str(exc)
    if "mạng" in message:
        return "network"
    if "xác thực" in message:
        return "auth"
    if "sai định dạng" in message:
        return "bad_response"
    return "http_error"
