"""Adapter DeepSeek (tắt suy luận, stream, thử lại) và bộ giới hạn đồng thời `LlmGate`. Không gọi mạng thật."""

import asyncio
import json
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError, DeepSeekChatCompletion
from src.infrastructure.ai.llm_gate import LlmGate
from src.infrastructure.observability import call_metrics
from src.infrastructure.observability.call_metrics import CallRecord, call_context


@pytest.fixture
def records() -> Iterator[list[CallRecord]]:
    captured: list[CallRecord] = []
    call_metrics.set_sink(captured.append)
    yield captured
    call_metrics.set_sink(None)


def _patch_httpx(monkeypatch: pytest.MonkeyPatch, handler: Any) -> None:
    real = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(handler), *args, **kwargs)  # noqa: B026

    monkeypatch.setattr(httpx, "AsyncClient", factory)


def _sse(*chunks: dict[str, Any]) -> str:
    return "".join(f"data: {json.dumps(chunk)}\n\n" for chunk in chunks) + "data: [DONE]\n\n"


def _delta(**delta: str) -> dict[str, Any]:
    return {"choices": [{"delta": delta, "finish_reason": None}]}


def _finish(reason: str = "stop", **usage: Any) -> list[dict[str, Any]]:
    return [
        {"choices": [{"delta": {}, "finish_reason": reason}]},
        {
            "choices": [],
            "usage": {
                "prompt_tokens": 2000,
                "completion_tokens": 500,
                "prompt_cache_hit_tokens": 1900,
                "completion_tokens_details": {"reasoning_tokens": 120},
                **usage,
            },
        },
    ]


def _llm(**kwargs: Any) -> DeepSeekChatCompletion:
    return DeepSeekChatCompletion(
        base_url="https://llm.test",
        api_key="khoa-bi-mat",
        model="deepseek-flash",
        gate=LlmGate(9, 5),
        backoff_seconds=(0.0,),
        **kwargs,
    )


async def test_reasoning_off_sends_thinking_disabled_and_stream_joins_chunks(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        body = _sse(
            _delta(reasoning_content="đang nghĩ"),
            _delta(content='{"a":'),
            _delta(content=" 1}"),
            *_finish(),
        )
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    _patch_httpx(monkeypatch, handler)

    with call_context(operation="task.proposal"):
        content = await _llm().complete_json(
            system_prompt="s", user_prompt="u", reasoning=False, stream=True, temperature=0.0
        )

    assert content == '{"a": 1}'
    assert seen["thinking"] == {"type": "disabled"} and seen["stream"] is True and seen["temperature"] == 0.0
    assert seen["stream_options"] == {"include_usage": True}
    (record,) = records
    assert record.ok and record.finish_reason == "stop" and record.attempt == 1
    assert (record.prompt_tokens, record.completion_tokens) == (2000, 500)
    assert (record.reasoning_tokens, record.cached_input_tokens) == (120, 1900)
    assert record.first_byte_ms is not None and record.first_token_ms is not None
    assert record.reasoning_ms is not None and record.content_ms is not None
    assert record.queue_wait_ms is not None
    assert "khoa-bi-mat" not in repr(record)


async def test_default_call_keeps_old_behaviour_no_thinking_field_no_stream(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "{}"}, "finish_reason": "stop"}]})

    _patch_httpx(monkeypatch, handler)

    assert await _llm().complete_json(system_prompt="s", user_prompt="u") == "{}"
    assert "thinking" not in seen and "stream" not in seen and "temperature" not in seen
    assert records[0].first_token_ms is None  # chỉ stream mới có số đo từng pha


async def test_stream_stopped_by_length_is_reported_not_returned_half_written(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=_sse(_delta(content='{"tasks": [{"title": "dở'), *_finish("length")))

    _patch_httpx(monkeypatch, handler)

    with pytest.raises(ChatCompletionError) as error:
        await _llm(max_retries=2).complete_json(system_prompt="s", user_prompt="u", reasoning=False, stream=True)

    assert error.value.code == "truncated" and not error.value.retryable
    assert len(records) == 1  # bị cắt do độ dài thì gọi lại cũng bị cắt: không thử lại


async def test_rate_limit_is_retried_and_attempt_number_is_recorded(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(429, text="quá tải")
        return httpx.Response(200, text=_sse(_delta(content="{}"), *_finish()))

    _patch_httpx(monkeypatch, handler)

    content = await _llm(max_retries=2).complete_json(system_prompt="s", user_prompt="u", reasoning=False, stream=True)

    assert content == "{}" and calls["n"] == 2
    assert [(r.ok, r.attempt, r.error) for r in records] == [(False, 1, "rate_limited"), (True, 2, None)]


async def test_retries_stop_after_max_and_auth_errors_are_never_retried(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    status = {"code": 503}
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(status["code"], text="lỗi")

    _patch_httpx(monkeypatch, handler)
    llm = _llm(max_retries=2)

    with pytest.raises(ChatCompletionError):
        await llm.complete_json(system_prompt="s", user_prompt="u")
    assert calls["n"] == 3  # 1 lần đầu + 2 lần thử lại

    calls["n"], status["code"] = 0, 401
    with pytest.raises(ChatCompletionError) as error:
        await llm.complete_json(system_prompt="s", user_prompt="u")
    assert calls["n"] == 1 and error.value.code == "auth"


async def test_timeout_is_retried_only_for_background_jobs(
    monkeypatch: pytest.MonkeyPatch, records: list[CallRecord]
) -> None:
    calls = {"n": 0}

    def handler(_: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("chậm")

    _patch_httpx(monkeypatch, handler)
    llm = _llm(max_retries=1)

    with pytest.raises(ChatCompletionError):  # người dùng Viga: đã chờ đủ, không chờ thêm
        await llm.complete_json(system_prompt="s", user_prompt="u")
    assert calls["n"] == 1

    calls["n"] = 0
    with call_context(operation="job", job_id=7), pytest.raises(ChatCompletionError):
        await llm.complete_json(system_prompt="s", user_prompt="u")
    assert calls["n"] == 2 and records[-1].error == "timeout"


async def test_gate_limits_total_and_background_concurrency_and_reports_wait() -> None:
    gate = LlmGate(total=3, background=2)
    running = {"bg": 0, "all": 0, "peak_bg": 0, "peak_all": 0}
    waits: list[float] = []

    async def work(background: bool) -> None:
        async with gate.slot(background=background) as waited:
            waits.append(waited)
            running["all"] += 1
            running["bg"] += int(background)
            running["peak_all"] = max(running["peak_all"], running["all"])
            running["peak_bg"] = max(running["peak_bg"], running["bg"])
            await asyncio.sleep(0.02)
            running["all"] -= 1
            running["bg"] -= int(background)

    await asyncio.gather(*(work(True) for _ in range(6)), *(work(False) for _ in range(3)))

    assert running["peak_bg"] <= 2 and running["peak_all"] <= 3 and gate.peak <= 3
    assert gate.in_flight == 0 and max(waits) > 0


async def test_background_queue_does_not_hold_shared_slots_so_interactive_calls_get_in() -> None:
    gate = LlmGate(total=2, background=1)
    release = asyncio.Event()
    order: list[str] = []

    async def background(name: str) -> None:
        async with gate.slot(background=True):
            order.append(name)
            await release.wait()

    first = asyncio.create_task(background("nền 1"))
    second = asyncio.create_task(background("nền 2"))
    await asyncio.sleep(0.01)
    async with asyncio.timeout(1):  # việc nền thứ hai đang xếp hàng nhưng không giữ chỗ chung: Viga vẫn vào được
        async with gate.slot(background=False):
            order.append("viga")
    release.set()
    await asyncio.gather(first, second)

    assert order == ["nền 1", "viga", "nền 2"]


def test_gate_rejects_invalid_limits() -> None:
    with pytest.raises(ValueError):
        LlmGate(0, 1)
