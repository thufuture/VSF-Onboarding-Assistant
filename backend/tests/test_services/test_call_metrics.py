"""Đo từng lần gọi LLM/embedding (mục 12, giai đoạn A): thời gian, token, chi phí ước tính; không bao giờ có nội dung (INV8)."""

import dataclasses
from collections.abc import Iterator
from typing import Any

import httpx
import pytest

from src.infrastructure.ai.deepseek_adapter import ChatCompletionError, DeepSeekChatCompletion
from src.infrastructure.observability import call_metrics
from src.infrastructure.observability.call_metrics import (
    CallRecord,
    call_context,
    collect_calls,
    emit,
    estimate_cost,
    set_prices,
    set_request_id,
    set_sink,
    set_user_id,
)
from src.services.ingest.embedding.modal_adapter import EmbeddingServiceError, ModalEmbeddingAdapter


@pytest.fixture(autouse=True)
def clean_metrics_state() -> Iterator[list[CallRecord]]:
    """Mỗi test có sink riêng và bảng giá riêng; trả lại trạng thái trống để không ảnh hưởng test khác."""
    sunk: list[CallRecord] = []
    set_sink(sunk.append)
    set_prices(llm_input_per_million=0.30, llm_output_per_million=1.20, embedding_per_thousand=0.0)
    yield sunk
    set_sink(None)
    set_prices(llm_input_per_million=0.0, llm_output_per_million=0.0, embedding_per_thousand=0.0)


def llm_record(**fields: Any) -> CallRecord:
    base: dict[str, Any] = {
        "kind": "llm",
        "provider": "deepseek",
        "model": "deepseek-flash",
        "latency_ms": 120.0,
        "ok": True,
    }
    return CallRecord(**{**base, **fields})


def test_cost_uses_the_configured_unit_prices() -> None:
    # Giá DeepSeek đã tra (mục 12.11a): 0,30 USD vào và 1,20 USD ra mỗi 1 triệu token.
    cost = estimate_cost(llm_record(prompt_tokens=2400, completion_tokens=300))

    assert cost == pytest.approx((2400 * 0.30 + 300 * 1.20) / 1_000_000)
    assert cost == pytest.approx(0.00108)  # ~27 đồng một câu hỏi đáp một ý


def test_cost_is_zero_when_prices_are_unknown() -> None:
    set_prices(llm_input_per_million=0.0, llm_output_per_million=0.0, embedding_per_thousand=0.0)

    assert estimate_cost(llm_record(prompt_tokens=10_000, completion_tokens=5_000)) == 0.0
    assert estimate_cost(CallRecord("embedding", "modal", "bge", 50.0, True, input_count=40)) == 0.0


def test_embedding_cost_is_per_thousand_inputs() -> None:
    set_prices(llm_input_per_million=0.0, llm_output_per_million=0.0, embedding_per_thousand=0.02)

    record = CallRecord("embedding", "modal", "bge-m3", 80.0, True, input_count=500)

    assert estimate_cost(record) == pytest.approx(0.01)


def test_emit_attaches_context_and_cost(clean_metrics_state: list[CallRecord]) -> None:
    set_user_id(7)
    set_request_id("req-abc")

    with call_context(operation="chat.answer"):
        emit(llm_record(prompt_tokens=1000, completion_tokens=100))

    (record,) = clean_metrics_state
    assert (record.operation, record.user_id, record.request_id) == ("chat.answer", 7, "req-abc")
    assert record.cost_usd == pytest.approx((1000 * 0.30 + 100 * 1.20) / 1_000_000)


def test_nested_context_overrides_operation_but_keeps_the_user(clean_metrics_state: list[CallRecord]) -> None:
    set_user_id(3)

    with call_context(operation="outer"):
        with call_context(operation="inner"):
            emit(llm_record())
        emit(llm_record())

    assert [r.operation for r in clean_metrics_state] == ["inner", "outer"]
    assert {r.user_id for r in clean_metrics_state} == {3}


def test_collect_calls_gathers_only_calls_made_inside_the_block() -> None:
    emit(llm_record(prompt_tokens=1))
    with collect_calls() as used:
        emit(llm_record(prompt_tokens=100, completion_tokens=10, latency_ms=50.0))
        emit(llm_record(prompt_tokens=200, completion_tokens=20, latency_ms=70.0))
    emit(llm_record(prompt_tokens=999))

    assert (used.prompt_tokens, used.completion_tokens, used.latency_ms) == (300, 30, 120.0)
    assert used.model == "deepseek-flash"


def test_a_failing_sink_never_breaks_the_caller() -> None:
    def broken(_: CallRecord) -> None:
        raise RuntimeError("không ghi được")

    set_sink(broken)

    emit(llm_record())  # đo lường không bao giờ được làm hỏng luồng chính


def test_records_never_carry_content_fields() -> None:
    """INV8: bản ghi chỉ có số liệu, không có trường nào chứa câu hỏi, tài liệu hay câu trả lời."""
    names = {field.name for field in dataclasses.fields(CallRecord)}

    assert names.isdisjoint({"prompt", "text", "content", "question", "answer", "response", "messages"})
    assert call_metrics.CallRecord.__name__ == "CallRecord"


def patch_httpx(monkeypatch: pytest.MonkeyPatch, module: Any, handler: Any) -> None:
    real = httpx.AsyncClient

    def factory(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return real(transport=httpx.MockTransport(handler), *args, **kwargs)  # noqa: B026

    monkeypatch.setattr(module.httpx, "AsyncClient", factory)


async def test_deepseek_adapter_records_tokens_latency_and_estimated_cost(
    monkeypatch: pytest.MonkeyPatch, clean_metrics_state: list[CallRecord]
) -> None:
    from src.infrastructure.ai import deepseek_adapter

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 2400, "completion_tokens": 300},
            },
        )

    patch_httpx(monkeypatch, deepseek_adapter, handler)
    llm = DeepSeekChatCompletion(base_url="https://llm.test", api_key="khoa-bi-mat", model="deepseek-flash")

    with call_context(operation="chat.answer"):
        content = await llm.complete_json(system_prompt="s", user_prompt="Câu hỏi riêng tư của nhân viên")

    assert content == '{"ok": true}'
    (record,) = clean_metrics_state
    assert record.ok and (record.prompt_tokens, record.completion_tokens) == (2400, 300)
    assert record.latency_ms >= 0
    assert record.cost_usd == pytest.approx(0.00108)
    assert "riêng tư" not in repr(record) and "khoa-bi-mat" not in repr(record)


@pytest.mark.parametrize(
    ("status", "expected_error"),
    [(401, "auth"), (500, "http_error")],
)
async def test_deepseek_adapter_records_http_failures_by_short_code(
    monkeypatch: pytest.MonkeyPatch, clean_metrics_state: list[CallRecord], status: int, expected_error: str
) -> None:
    from src.infrastructure.ai import deepseek_adapter

    patch_httpx(monkeypatch, deepseek_adapter, lambda _: httpx.Response(status, text="lỗi"))
    llm = DeepSeekChatCompletion(base_url="https://llm.test", api_key="k", model="m")

    with pytest.raises(ChatCompletionError):
        await llm.complete_json(system_prompt="s", user_prompt="u")

    (record,) = clean_metrics_state
    assert record.ok is False and record.error == expected_error
    assert record.prompt_tokens == 0


async def test_deepseek_adapter_records_network_errors(
    monkeypatch: pytest.MonkeyPatch, clean_metrics_state: list[CallRecord]
) -> None:
    from src.infrastructure.ai import deepseek_adapter

    def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("không nối được")

    patch_httpx(monkeypatch, deepseek_adapter, handler)
    llm = DeepSeekChatCompletion(base_url="https://llm.test", api_key="k", model="m")

    with pytest.raises(ChatCompletionError):
        await llm.complete_json(system_prompt="s", user_prompt="u")

    assert clean_metrics_state[0].error == "network"


def embedding_adapter(max_attempts: int = 1) -> ModalEmbeddingAdapter:
    return ModalEmbeddingAdapter(
        endpoint="https://embed.test",
        api_key="khoa",
        connect_timeout=1,
        read_timeout=1,
        max_attempts=max_attempts,
        backoff_initial=0,
        backoff_multiplier=1,
        backoff_max=0,
    )


async def test_modal_adapter_records_input_count_for_embedding_cost(
    monkeypatch: pytest.MonkeyPatch, clean_metrics_state: list[CallRecord]
) -> None:
    from src.services.ingest.embedding import modal_adapter

    def handler(request: httpx.Request) -> httpx.Response:
        count = len(__import__("json").loads(request.content)["texts"])
        return httpx.Response(
            200, json={"vectors": [[0.0] * 1024] * count, "model_version": "bge-m3-v1", "dimension": 1024}
        )

    patch_httpx(monkeypatch, modal_adapter, handler)
    adapter = embedding_adapter()

    with call_context(operation="ingest.embed"):
        vectors = await adapter.embed([f"đoạn {i}" for i in range(40)])

    assert len(vectors) == 40
    (record,) = clean_metrics_state
    assert record.kind == "embedding" and record.input_count == 40 and record.ok
    assert record.operation == "ingest.embed"


async def test_modal_adapter_records_failures(
    monkeypatch: pytest.MonkeyPatch, clean_metrics_state: list[CallRecord]
) -> None:
    from src.services.ingest.embedding import modal_adapter

    patch_httpx(monkeypatch, modal_adapter, lambda _: httpx.Response(500))
    adapter = embedding_adapter()

    with pytest.raises(EmbeddingServiceError):
        await adapter.embed(["một đoạn"])

    (record,) = clean_metrics_state
    assert record.ok is False and record.error == "embedding_error" and record.input_count == 1
