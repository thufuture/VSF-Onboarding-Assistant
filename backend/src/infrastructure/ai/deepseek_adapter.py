"""Adapter gọi DeepSeek qua giao diện tương thích OpenAI (`POST /chat/completions`,
`response_format: {"type": "json_object"}`). Đã gọi thử thật trước khi viết adapter (bắt buộc theo
master-plan): model `deepseek-flash` trả `200`, hỗ trợ JSON mode; trường `reasoning_content` (suy luận
nội bộ) bị bỏ qua, chỉ lấy `content` (JSON cuối cùng).

Tối ưu độ trễ tạo task bằng AI (kế hoạch `Ai-task/ke-hoach-toi-uu-tao-task-bang-ai.md`):
- `reasoning=False` gửi `"thinking": {"type": "disabled"}` — đo thật: suy luận ẩn chiếm 83–86% thời gian của lời gọi soạn task;
- `stream=True` đọc từng đoạn để ghi thời điểm byte đầu, chữ đầu, pha suy luận/viết (vào `llm_calls`) và dùng timeout "im lặng"
  (không có đoạn nào trong `idle_seconds`) thay vì chỉ một timeout tổng; kiểm tra `finish_reason == "stop"` (bị cắt do độ dài thì báo lỗi);
- mọi lời gọi đi qua `LlmGate` (tối đa 9 cùng lúc, việc nền tối đa 5) và được thử lại khi 429/5xx/mất kết nối (và hết giờ với việc nền).
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass

import httpx

from src.infrastructure.ai.llm_gate import LlmGate, shared_gate
from src.infrastructure.observability.call_metrics import (
    CallObservation,
    CallRecord,
    current_job_id,
    emit,
    observe_start,
)

DEFAULT_IDLE_SECONDS = 30.0
RETRY_BACKOFF_SECONDS = (1.0, 3.0)


class ChatCompletionError(Exception):
    """Lỗi khi gọi LLM — người gọi phải coi như "chưa có căn cứ", không hiển thị câu trả lời chưa kiểm chứng.

    `code` là mã ngắn để thống kê (không chứa nội dung); `retryable` cho biết thử lại có thể thành công.
    """

    def __init__(self, message: str, *, code: str = "http_error", retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass
class _CallStats:
    """Số đo của một lời gọi (chỉ điền đủ khi gọi bằng stream)."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    reasoning_tokens: int = 0
    cached_input_tokens: int = 0
    finish_reason: str | None = None
    first_byte_ms: float | None = None
    first_token_ms: float | None = None
    reasoning_ms: float | None = None
    content_ms: float | None = None


class DeepSeekChatCompletion:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float = 60,
        max_retries: int = 0,
        idle_seconds: float = DEFAULT_IDLE_SECONDS,
        gate: LlmGate | None = None,
        backoff_seconds: tuple[float, ...] = RETRY_BACKOFF_SECONDS,
    ) -> None:
        if not base_url or not api_key or not model:
            raise ValueError("cần LLM_BASE_URL, LLM_API_KEY, LLM_MODEL")
        self._url = f"{base_url.rstrip('/')}/chat/completions"
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._idle = idle_seconds
        self._gate = gate
        self._backoff = backoff_seconds

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
        timeout = timeout_seconds or self._timeout
        background = current_job_id() is not None
        gate = self._gate or shared_gate(9, 5)
        attempt = 0
        while True:
            attempt += 1
            delay: float | None = None
            async with gate.slot(background=background) as waited_ms:
                observation = observe_start(
                    "llm",
                    self._model,
                    [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
                )
                started = time.perf_counter()
                try:
                    if stream:
                        content, stats = await self._complete_stream(
                            system_prompt, user_prompt, started, timeout, reasoning, temperature
                        )
                    else:
                        content, stats = await self._complete_plain(
                            system_prompt, user_prompt, timeout, reasoning, temperature
                        )
                except ChatCompletionError as exc:
                    self._emit(
                        started,
                        _CallStats(),
                        ok=False,
                        error=exc.code,
                        attempt=attempt,
                        waited_ms=waited_ms,
                        observation=observation,
                    )
                    if not self._should_retry(exc, attempt, background):
                        raise
                    delay = self._backoff[min(attempt - 1, len(self._backoff) - 1)] if self._backoff else 0.0
                else:
                    self._emit(
                        started,
                        stats,
                        ok=True,
                        attempt=attempt,
                        waited_ms=waited_ms,
                        observation=observation,
                        output=content,
                    )
                    return content
            # Chờ ngoài bộ giới hạn để không giữ chỗ của lời gọi khác trong lúc nghỉ.
            await asyncio.sleep(delay or 0.0)

    def _should_retry(self, exc: ChatCompletionError, attempt: int, background: bool) -> bool:
        if attempt > self._max_retries or not exc.retryable:
            return False
        # Hết giờ: người dùng Viga đã chờ đủ lâu rồi, chỉ việc nền mới thử lại.
        return exc.code != "timeout" or background

    def _emit(
        self,
        started: float,
        stats: _CallStats,
        *,
        ok: bool,
        error: str | None = None,
        attempt: int = 1,
        waited_ms: float | None = None,
        observation: CallObservation | None = None,
        output: str | None = None,
    ) -> None:
        emit(
            CallRecord(
                kind="llm",
                provider="deepseek",
                model=self._model,
                latency_ms=(time.perf_counter() - started) * 1000,
                ok=ok,
                prompt_tokens=stats.prompt_tokens,
                completion_tokens=stats.completion_tokens,
                error=error,
                first_byte_ms=stats.first_byte_ms,
                first_token_ms=stats.first_token_ms,
                reasoning_ms=stats.reasoning_ms,
                content_ms=stats.content_ms,
                reasoning_tokens=stats.reasoning_tokens,
                cached_input_tokens=stats.cached_input_tokens,
                finish_reason=stats.finish_reason,
                attempt=attempt,
                queue_wait_ms=waited_ms,
            ),
            observation,
            output,
        )

    def _body(
        self, system_prompt: str, user_prompt: str, *, reasoning: bool, stream: bool, temperature: float | None = None
    ) -> dict[str, object]:
        body: dict[str, object] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        if temperature is not None:
            body["temperature"] = temperature
        if not reasoning:
            body["thinking"] = {"type": "disabled"}
        if stream:
            body["stream"] = True
            body["stream_options"] = {"include_usage": True}
        return body

    def _check_status(self, status: int, text: str) -> None:
        if status in (401, 403):
            raise ChatCompletionError(f"LLM từ chối xác thực ({status}) — kiểm tra LLM_API_KEY", code="auth")
        if status == 429:
            raise ChatCompletionError("LLM đang quá tải (429)", code="rate_limited", retryable=True)
        if status >= 500:
            raise ChatCompletionError(f"LLM lỗi: {status} {text[:200]}", code="http_error", retryable=True)
        if status != 200:
            raise ChatCompletionError(f"LLM lỗi: {status} {text[:200]}", code="http_error")

    async def _complete_plain(
        self, system_prompt: str, user_prompt: str, timeout: float, reasoning: bool, temperature: float | None
    ) -> tuple[str, _CallStats]:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self._url,
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=self._body(
                        system_prompt, user_prompt, reasoning=reasoning, stream=False, temperature=temperature
                    ),
                    timeout=timeout,
                )
            except httpx.TimeoutException as exc:
                raise ChatCompletionError(f"LLM hết giờ chờ: {exc}", code="timeout", retryable=True) from exc
            except (httpx.ConnectError, httpx.NetworkError) as exc:
                raise ChatCompletionError(f"lỗi mạng khi gọi LLM: {exc}", code="network", retryable=True) from exc
        self._check_status(response.status_code, response.text)
        try:
            data = response.json()
            choice = data["choices"][0]
            content = str(choice["message"]["content"])
        except (ValueError, KeyError, IndexError) as exc:
            raise ChatCompletionError(f"phản hồi LLM sai định dạng: {exc}", code="bad_response") from exc
        usage = data.get("usage") if isinstance(data, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        details = usage.get("completion_tokens_details")
        stats = _CallStats(
            prompt_tokens=int(usage.get("prompt_tokens") or 0),
            completion_tokens=int(usage.get("completion_tokens") or 0),
            reasoning_tokens=int((details or {}).get("reasoning_tokens") or 0) if isinstance(details, dict) else 0,
            cached_input_tokens=int(usage.get("prompt_cache_hit_tokens") or 0),
            finish_reason=str(choice.get("finish_reason")) if choice.get("finish_reason") else None,
        )
        return content, stats

    async def _complete_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        started: float,
        timeout: float,
        reasoning: bool,
        temperature: float | None,
    ) -> tuple[str, _CallStats]:
        """Đọc kết quả theo từng đoạn. Nội dung nối lại giống hệt lời gọi thường; thêm số đo từng pha."""
        stats = _CallStats()
        parts: list[str] = []
        first_reasoning: float | None = None
        first_content: float | None = None
        try:
            async with asyncio.timeout(timeout):
                async with httpx.AsyncClient() as client:
                    async with client.stream(
                        "POST",
                        self._url,
                        headers={"Authorization": f"Bearer {self._api_key}"},
                        json=self._body(
                            system_prompt, user_prompt, reasoning=reasoning, stream=True, temperature=temperature
                        ),
                        timeout=httpx.Timeout(timeout, connect=10, read=self._idle),
                    ) as response:
                        if response.status_code != 200:
                            text = (await response.aread()).decode("utf-8", "replace")
                            self._check_status(response.status_code, text)
                        async for line in response.aiter_lines():
                            if not line.startswith("data:"):
                                continue
                            now = (time.perf_counter() - started) * 1000
                            if stats.first_byte_ms is None:
                                stats.first_byte_ms = now
                            payload = line[5:].strip()
                            if payload == "[DONE]":
                                break
                            try:
                                chunk = json.loads(payload)
                            except ValueError as exc:
                                raise ChatCompletionError(
                                    f"đoạn phản hồi LLM sai định dạng: {exc}", code="bad_response"
                                ) from exc
                            usage = chunk.get("usage")
                            if isinstance(usage, dict):
                                self._read_usage(stats, usage)
                            for choice in chunk.get("choices") or []:
                                delta = choice.get("delta") or {}
                                if delta.get("reasoning_content") and first_reasoning is None:
                                    first_reasoning = now
                                if delta.get("content"):
                                    if first_content is None:
                                        first_content = now
                                    parts.append(str(delta["content"]))
                                if choice.get("finish_reason"):
                                    stats.finish_reason = str(choice["finish_reason"])
        except TimeoutError as exc:
            raise ChatCompletionError("LLM hết giờ chờ", code="timeout", retryable=True) from exc
        except httpx.TimeoutException as exc:
            raise ChatCompletionError(f"LLM im lặng quá {self._idle:.0f} giây", code="timeout", retryable=True) from exc
        except (httpx.ConnectError, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            raise ChatCompletionError(f"lỗi mạng khi gọi LLM: {exc}", code="network", retryable=True) from exc

        total_ms = (time.perf_counter() - started) * 1000
        if first_content is not None:
            stats.first_token_ms = first_content
            stats.content_ms = max(0.0, total_ms - first_content)
            if first_reasoning is not None:
                stats.reasoning_ms = max(0.0, first_content - first_reasoning)
        content = "".join(parts)
        if stats.finish_reason not in (None, "stop"):
            # "length" nghĩa là JSON bị cắt giữa chừng: không dùng được, và gọi lại y nguyên cũng sẽ bị cắt.
            raise ChatCompletionError(f"LLM dừng sớm ({stats.finish_reason})", code="truncated")
        if not content:
            raise ChatCompletionError("phản hồi LLM rỗng", code="bad_response")
        return content, stats

    @staticmethod
    def _read_usage(stats: _CallStats, usage: dict[str, object]) -> None:
        stats.prompt_tokens = int(usage.get("prompt_tokens") or 0)  # type: ignore[call-overload]
        stats.completion_tokens = int(usage.get("completion_tokens") or 0)  # type: ignore[call-overload]
        stats.cached_input_tokens = int(usage.get("prompt_cache_hit_tokens") or 0)  # type: ignore[call-overload]
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            stats.reasoning_tokens = int(details.get("reasoning_tokens") or 0)
