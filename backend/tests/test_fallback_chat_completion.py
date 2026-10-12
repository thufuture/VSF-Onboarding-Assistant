"""Lớp dự phòng LLM: chỉ chuyển khi lỗi hạ tầng, ngắt mạch dùng chung, việc nền không dùng dự phòng trừ khi cho phép."""

from typing import Any

import pytest

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError, extract_json_text
from src.infrastructure.ai.fallback_chat_completion import CircuitBreaker, FallbackChatCompletion


class _Llm:
    def __init__(self, reply: str = "{}", error: ChatCompletionError | None = None) -> None:
        self.reply = reply
        self.error = error
        self.calls = 0

    async def complete_json(self, **kwargs: Any) -> str:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.reply


class _Clock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


def _breaker(clock: _Clock, threshold: int = 2) -> CircuitBreaker:
    return CircuitBreaker(failure_threshold=threshold, cooldown_seconds=30, clock=clock)


async def _ask(llm: FallbackChatCompletion) -> str:
    return await llm.complete_json(system_prompt="s", user_prompt="u")


@pytest.mark.asyncio
async def test_primary_success_does_not_touch_secondary() -> None:
    primary, secondary = _Llm('{"a":1}'), _Llm('{"b":2}')

    assert await _ask(FallbackChatCompletion(primary, secondary, _breaker(_Clock()))) == '{"a":1}'
    assert secondary.calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("code", ["timeout", "network", "rate_limited", "http_error", "auth"])
async def test_infrastructure_errors_fall_back(code: str) -> None:
    primary = _Llm(error=ChatCompletionError("x", code=code, retryable=True))
    secondary = _Llm('{"b":2}')

    assert await _ask(FallbackChatCompletion(primary, secondary, _breaker(_Clock()))) == '{"b":2}'
    assert secondary.calls == 1


@pytest.mark.asyncio
async def test_content_errors_do_not_fall_back() -> None:
    primary = _Llm(error=ChatCompletionError("sai định dạng", code="bad_response"))
    secondary = _Llm()

    with pytest.raises(ChatCompletionError):
        await _ask(FallbackChatCompletion(primary, secondary, _breaker(_Clock())))
    assert secondary.calls == 0


@pytest.mark.asyncio
async def test_breaker_skips_primary_after_repeated_failures_then_recovers() -> None:
    clock = _Clock()
    primary = _Llm(error=ChatCompletionError("x", code="timeout", retryable=True))
    secondary = _Llm('{"b":2}')
    llm = FallbackChatCompletion(primary, secondary, _breaker(clock, threshold=2))

    await _ask(llm)
    await _ask(llm)  # lỗi thứ hai mở bộ ngắt
    primary_calls = primary.calls
    await _ask(llm)  # bộ ngắt mở: không gọi nhà cung cấp chính
    assert primary.calls == primary_calls

    clock.now = 31  # hết thời gian nghỉ: thử lại nhà cung cấp chính
    primary.error = None
    primary.reply = '{"a":1}'
    assert await _ask(llm) == '{"a":1}'
    assert primary.calls == primary_calls + 1


@pytest.mark.asyncio
async def test_secondary_error_propagates() -> None:
    primary = _Llm(error=ChatCompletionError("x", code="timeout", retryable=True))
    secondary = _Llm(error=ChatCompletionError("y", code="http_error", retryable=True))

    with pytest.raises(ChatCompletionError):
        await _ask(FallbackChatCompletion(primary, secondary, _breaker(_Clock())))


@pytest.mark.asyncio
async def test_background_jobs_use_fallback_only_when_allowed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.ai.fallback_chat_completion.current_job_id", lambda: 7)
    error = ChatCompletionError("x", code="timeout", retryable=True)

    denied_secondary = _Llm('{"b":2}')
    with pytest.raises(ChatCompletionError):
        await _ask(FallbackChatCompletion(_Llm(error=error), denied_secondary, _breaker(_Clock())))
    assert denied_secondary.calls == 0

    allowed_secondary = _Llm('{"b":2}')
    result = await _ask(
        FallbackChatCompletion(_Llm(error=error), allowed_secondary, _breaker(_Clock()), allow_background=True)
    )
    assert result == '{"b":2}'


def test_extract_json_text_strips_markdown_fence() -> None:
    assert extract_json_text('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json_text('Đây là kết quả: {"a": {"b": 2}} xong') == '{"a": {"b": 2}}'
    assert extract_json_text("không có json") == "không có json"


def test_fallback_adapter_body_has_no_json_mode_and_uses_openrouter_reasoning_flag() -> None:
    from src.infrastructure.ai.deepseek_adapter import DeepSeekChatCompletion

    llm = DeepSeekChatCompletion(
        base_url="https://openrouter.ai/api/v1",
        api_key="k",
        model="anthropic/claude-haiku-5.5",
        provider_name="fallback",
        reasoning_style="openrouter",
        json_mode=False,
        supports_stream=False,
        max_output_tokens=4000,
    )

    body = llm._body("s", "u", reasoning=False, stream=False)  # noqa: SLF001

    assert "response_format" not in body
    assert body["reasoning"] == {"enabled": False}
    assert "thinking" not in body
    assert body["max_tokens"] == 4000


def test_primary_adapter_body_unchanged() -> None:
    from src.infrastructure.ai.deepseek_adapter import DeepSeekChatCompletion

    body = DeepSeekChatCompletion(base_url="https://api.deepseek.com", api_key="k", model="m")._body(  # noqa: SLF001
        "s", "u", reasoning=False, stream=False
    )

    assert body["response_format"] == {"type": "json_object"}
    assert body["thinking"] == {"type": "disabled"}
    assert "max_tokens" not in body and "reasoning" not in body
