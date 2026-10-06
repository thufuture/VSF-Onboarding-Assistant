"""Theo dõi toàn bộ lộ trình xử lý bằng Langfuse: câu hỏi chat/Viga, việc nền (tạo task bằng AI, nạp tài liệu), từng lời
gọi LLM/embedding với input, output, độ trễ, token và chi phí.

Cấu trúc một trace: một **gốc** (`trace()` hoặc span ngoài cùng) chứa các bước (`span()`), mỗi lời gọi dịch vụ ngoài là một
`generation`/`embedding` con do adapter mở qua `call_metrics.observe_start()`.

Nội dung (input/output) là dữ liệu của nhân viên và tài liệu nội bộ, đi ra dịch vụ ngoài, nên chỉ được gửi khi
`LANGFUSE_CAPTURE_CONTENT=true`; mặc định tắt thì chỉ gửi số liệu (độ dài, số lượng, token, chi phí, thời gian). Khi bật, mỗi
chuỗi bị cắt ở `LANGFUSE_CONTENT_MAX_CHARS` ký tự.

`LANGFUSE_ENABLED=false` (hoặc chưa có khóa) -> mọi thao tác là no-op, không gọi mạng. Lỗi của Langfuse (mạng, khóa sai...)
không bao giờ được làm hỏng luồng chính: mọi lỗi bị nuốt và ghi log.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from src.infrastructure.observability.call_metrics import CallObservation, CallRecord

logger = logging.getLogger(__name__)


class _SpanHandle(Protocol):
    def update(self, **fields: Any) -> None: ...


class _NoopSpan:
    def update(self, **fields: Any) -> None:
        pass


class _CallObservation:
    """Một lời gọi LLM/embedding đang chạy: mở trước khi gọi, đóng ngay sau khi gọi nên thời gian là thời gian thật."""

    def __init__(self, tracer: LangfuseTracer, observation: Any) -> None:
        self._tracer = tracer
        self._observation = observation

    def finish(self, record: CallRecord, output: Any = None) -> None:
        try:
            fields: dict[str, Any] = {
                "output": self._tracer.clip(output),
                "metadata": {
                    "operation": record.operation,
                    "provider": record.provider,
                    "latency_ms": round(record.latency_ms),
                    "attempt": record.attempt,
                    "queue_wait_ms": None if record.queue_wait_ms is None else round(record.queue_wait_ms),
                    "first_token_ms": None if record.first_token_ms is None else round(record.first_token_ms),
                    "reasoning_ms": None if record.reasoning_ms is None else round(record.reasoning_ms),
                    "finish_reason": record.finish_reason,
                    "job_id": record.job_id,
                    "request_id": record.request_id,
                },
            }
            if record.kind == "llm":
                usage = {"input": record.prompt_tokens, "output": record.completion_tokens}
                if record.reasoning_tokens:
                    usage["reasoning"] = record.reasoning_tokens
                if record.cached_input_tokens:
                    usage["cached_input"] = record.cached_input_tokens
                fields["usage_details"] = usage
            else:
                fields["usage_details"] = {"input": record.input_count}
            if record.cost_usd:
                fields["cost_details"] = {"total": record.cost_usd}
            if not record.ok:
                fields["level"] = "ERROR"
                fields["status_message"] = record.error
            self._observation.update(**fields)
            self._observation.end()
        except Exception:
            logger.warning("Không ghi được lời gọi vào Langfuse.", exc_info=True)


class LangfuseTracer:
    def __init__(
        self,
        *,
        enabled: bool,
        public_key: str | None,
        secret_key: str | None,
        host: str | None,
        capture_content: bool = False,
        content_max_chars: int = 4000,
    ) -> None:
        self._client: Any = None
        self._capture = capture_content
        self._max_chars = content_max_chars
        if enabled and public_key and secret_key:
            try:
                from langfuse import Langfuse

                self._client = Langfuse(public_key=public_key, secret_key=secret_key, host=host)
            except Exception:  # SDK lỗi cài đặt/khởi tạo không được chặn luồng chính
                logger.warning("Không khởi tạo được Langfuse, tắt theo dõi cho phiên này.", exc_info=True)
                self._client = None

    @property
    def active(self) -> bool:
        return self._client is not None

    def clip(self, value: Any) -> Any:
        """Nội dung đưa lên Langfuse: bỏ hẳn khi không bật `capture_content`, cắt ngắn khi bật."""
        if not self._capture or value is None:
            return None
        if isinstance(value, str):
            return (
                value
                if len(value) <= self._max_chars
                else value[: self._max_chars] + f"… (+{len(value) - self._max_chars} ký tự)"
            )
        if isinstance(value, dict):
            return {str(k): self.clip(v) for k, v in value.items()}
        if isinstance(value, list | tuple):
            return [self.clip(v) for v in list(value)[:50]]
        return value

    def flush(self) -> None:
        if self._client is not None:
            try:
                self._client.flush()
            except Exception:
                logger.warning("Không đẩy hết dữ liệu lên Langfuse.", exc_info=True)

    def start_call(self, kind: str, model: str, operation: str, input_value: Any) -> CallObservation | None:
        """Mở một generation/embedding con của span hiện tại (không đặt làm span hiện tại)."""
        if self._client is None:
            return None
        try:
            observation = self._client.start_observation(
                name=operation,
                as_type="generation" if kind == "llm" else "embedding",
                model=model,
                input=self.clip(input_value),
                metadata={"started_at": datetime.now(UTC).isoformat()},
            )
            return _CallObservation(self, observation)
        except Exception:
            logger.warning("Không mở được lời gọi trong Langfuse.", exc_info=True)
            return None

    @contextmanager
    def span(
        self,
        name: str,
        *,
        metadata: dict[str, Any] | None = None,
        as_type: str = "span",
        input: Any = None,  # noqa: A002 - cùng tên tham số với SDK Langfuse
        user_id: int | None = None,
        session_id: str | None = None,
        tags: list[str] | None = None,
    ) -> Iterator[_SpanHandle]:
        """Một bước xử lý. Nằm trong bước/gốc đang mở thì thành con của nó, không thì là gốc của một trace mới."""
        if self._client is None:
            yield _NoopSpan()
            return

        # Chỉ bọc try/except quanh việc MỞ span thật (lỗi SDK/mạng của Langfuse) — không được bọc quanh
        # `yield`, vì lỗi ném vào từ bên trong khối `with tracer.span(...)` (luồng chính) phải được
        # truyền tiếp nguyên vẹn, không bị nuốt hay biến thành "generator didn't stop after throw()".
        try:
            from langfuse import propagate_attributes

            attrs: dict[str, Any] = {}
            if user_id is not None:
                attrs["user_id"] = str(user_id)
            if session_id is not None:
                attrs["session_id"] = session_id
            if tags:
                attrs["tags"] = tags
            attr_cm = propagate_attributes(trace_name=name, **attrs) if attrs or _is_root(self._client) else None
            if attr_cm is not None:
                attr_cm.__enter__()
            span_cm = self._client.start_as_current_observation(
                name=name, as_type=as_type, metadata=metadata, input=self.clip(input)
            )
            span = span_cm.__enter__()
        except Exception:
            logger.warning("Không mở được Langfuse span '%s', bỏ qua theo dõi bước này.", name, exc_info=True)
            yield _NoopSpan()
            return

        try:
            yield _ClippedSpan(self, span)
        except BaseException:
            _close(span_cm, sys.exc_info())
            _close(attr_cm, sys.exc_info())
            raise
        else:
            _close(span_cm, (None, None, None))
            _close(attr_cm, (None, None, None))


class _ClippedSpan:
    """Bọc span thật: `output`/`input` đi qua `clip` để tôn trọng cấu hình có gửi nội dung hay không."""

    def __init__(self, tracer: LangfuseTracer, span: Any) -> None:
        self._tracer = tracer
        self._span = span

    def update(self, **fields: Any) -> None:
        try:
            for key in ("input", "output"):
                if key in fields:
                    fields[key] = self._tracer.clip(fields[key])
            self._span.update(**fields)
        except Exception:
            logger.warning("Không cập nhật được Langfuse span.", exc_info=True)


def _is_root(client: Any) -> bool:
    try:
        return bool(client.get_current_trace_id() is None)
    except Exception:
        return True


def _close(cm: Any, exc_info: Any) -> None:
    if cm is None:
        return
    try:
        cm.__exit__(*exc_info)
    except Exception:
        logger.warning("Không đóng được Langfuse span.", exc_info=True)


_current: LangfuseTracer | None = None


def set_current_tracer(tracer: LangfuseTracer | None) -> None:
    """Đăng ký tracer dùng chung cho nơi không nhận được qua tham số (việc nền, adapter)."""
    global _current
    _current = tracer


def current_tracer() -> LangfuseTracer:
    return _current or _DISABLED


_DISABLED = LangfuseTracer(enabled=False, public_key=None, secret_key=None, host=None)
