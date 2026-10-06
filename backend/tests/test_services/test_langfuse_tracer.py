"""Bộ theo dõi Langfuse: gửi nội dung chỉ khi được bật, mỗi lời gọi là một generation có token/chi phí/độ trễ, lỗi Langfuse không làm hỏng luồng chính."""

from typing import Any

import pytest

from src.infrastructure.observability import call_metrics
from src.infrastructure.observability.call_metrics import CallRecord, emit, observe_start, set_observer
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer


class FakeObservation:
    def __init__(self, name: str, kwargs: dict[str, Any]) -> None:
        self.name = name
        self.kwargs = kwargs
        self.updates: list[dict[str, Any]] = []
        self.ended = False

    def update(self, **fields: Any) -> None:
        self.updates.append(fields)

    def end(self) -> None:
        self.ended = True

    def __enter__(self) -> "FakeObservation":
        return self

    def __exit__(self, *exc: object) -> None:
        self.ended = True


class FakeClient:
    def __init__(self) -> None:
        self.opened: list[FakeObservation] = []

    def start_as_current_observation(self, **kwargs: Any) -> FakeObservation:
        obs = FakeObservation(kwargs["name"], kwargs)
        self.opened.append(obs)
        return obs

    def start_observation(self, **kwargs: Any) -> FakeObservation:
        obs = FakeObservation(kwargs["name"], kwargs)
        self.opened.append(obs)
        return obs

    def get_current_trace_id(self) -> None:
        return None


def make(capture: bool, max_chars: int = 20) -> tuple[LangfuseTracer, FakeClient]:
    tracer = LangfuseTracer(
        enabled=False, public_key=None, secret_key=None, host=None, capture_content=capture, content_max_chars=max_chars
    )
    client = FakeClient()
    tracer._client = client  # noqa: SLF001 - thay client thật bằng client giả
    return tracer, client


def test_content_is_dropped_unless_capture_is_enabled() -> None:
    off, _ = make(False)
    on, _ = make(True)

    assert off.clip("câu hỏi của nhân viên") is None
    assert on.clip("ngắn") == "ngắn"


def test_long_text_is_clipped_and_lists_are_capped() -> None:
    tracer, _ = make(True, max_chars=10)

    clipped = tracer.clip({"q": "x" * 50, "items": list(range(80))})

    assert clipped["q"].startswith("x" * 10) and "+40" in clipped["q"]
    assert len(clipped["items"]) == 50


def test_llm_call_becomes_a_generation_with_usage_cost_and_latency(monkeypatch: pytest.MonkeyPatch) -> None:
    tracer, client = make(True)
    set_observer(tracer.start_call)
    try:
        observation = observe_start("llm", "deepseek-flash", [{"role": "user", "content": "hỏi"}])
        emit(
            CallRecord(
                kind="llm",
                provider="deepseek",
                model="deepseek-flash",
                latency_ms=1234.4,
                ok=True,
                prompt_tokens=100,
                completion_tokens=20,
            ),
            observation,
            "đáp",
        )
    finally:
        set_observer(None)

    (generation,) = client.opened
    assert generation.kwargs["as_type"] == "generation" and generation.kwargs["model"] == "deepseek-flash"
    assert generation.kwargs["input"] == [{"role": "user", "content": "hỏi"}]
    fields = generation.updates[0]
    assert fields["output"] == "đáp"
    assert fields["usage_details"] == {"input": 100, "output": 20}
    assert fields["metadata"]["latency_ms"] == 1234
    assert generation.ended


def test_failed_call_is_marked_as_error_and_metadata_only_mode_hides_content() -> None:
    tracer, client = make(False)
    set_observer(tracer.start_call)
    try:
        observation = observe_start("embedding", "bge-m3", {"texts": ["bí mật"]})
        emit(
            CallRecord(
                kind="embedding",
                provider="modal",
                model="bge-m3",
                latency_ms=5,
                ok=False,
                input_count=3,
                error="embedding_error",
            ),
            observation,
            None,
        )
    finally:
        set_observer(None)

    (call,) = client.opened
    assert call.kwargs["as_type"] == "embedding" and call.kwargs["input"] is None
    assert call.updates[0]["level"] == "ERROR" and call.updates[0]["status_message"] == "embedding_error"
    assert call.updates[0]["usage_details"] == {"input": 3}


def test_spans_nest_and_errors_inside_propagate_unchanged() -> None:
    tracer, client = make(True)

    with pytest.raises(ValueError, match="boom"):
        with tracer.span("root", input="câu hỏi"):
            with tracer.span("child") as child:
                child.update(output={"ok": True})
            raise ValueError("boom")

    assert [o.name for o in client.opened] == ["root", "child"]
    assert all(o.ended for o in client.opened)
    assert client.opened[1].updates[0]["output"] == {"ok": True}


def test_disabled_tracer_is_a_noop() -> None:
    tracer = LangfuseTracer(enabled=False, public_key=None, secret_key=None, host=None)

    with tracer.span("anything", input="x") as span:
        span.update(output="y")
    assert tracer.start_call("llm", "m", "op", "x") is None
    assert call_metrics.observe_start("llm", "m", "x") is None
