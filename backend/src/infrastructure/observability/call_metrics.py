"""Đo từng lần gọi dịch vụ ngoài tốn tiền (LLM, embedding): thời gian, token, thành công hay lỗi.

Chỉ ghi **số liệu**, không bao giờ ghi nội dung câu hỏi/tài liệu/câu trả lời (INV8). Adapter gọi `emit()` sau mỗi lần
gọi (kể cả lỗi); ngữ cảnh (đang làm việc gì, của ai, request nào) lấy từ `call_context()` do router/service đặt.

- `set_sink()` đăng ký nơi nhận bản ghi (ghi bảng `llm_calls`); chưa đăng ký thì `emit()` chỉ gom cho `collect_calls()`.
- `collect_calls()` gom các bản ghi phát sinh trong một khối `with` để gắn vào span Langfuse.
- `observe_start()` + `emit(..., observation=, output=)` đưa từng lời gọi (kèm nội dung nếu được bật) lên Langfuse.
- Mọi lỗi của lớp đo đều bị nuốt: đo lường không bao giờ được làm hỏng luồng chính.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from typing import Any, Protocol

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CallContext:
    operation: str = "unknown"
    user_id: int | None = None
    request_id: str | None = None
    # Việc nền đang chạy (nếu có): để cộng chi phí và độ trễ theo từng lượt tạo task hoặc kích hoạt tài liệu.
    job_id: int | None = None


@dataclass(frozen=True)
class CallRecord:
    kind: str  # "llm" | "embedding"
    provider: str
    model: str
    latency_ms: float
    ok: bool
    prompt_tokens: int = 0
    completion_tokens: int = 0
    input_count: int = 0  # số chuỗi gửi đi (embedding)
    error: str | None = None  # mã lỗi ngắn, không chứa nội dung
    operation: str = "unknown"
    user_id: int | None = None
    request_id: str | None = None
    cost_usd: float = 0.0
    job_id: int | None = None
    # Số đo từng pha của một lời gọi LLM (chỉ có khi gọi ở chế độ stream; mục 14.3 của kế hoạch tối ưu). Không chứa nội dung.
    first_byte_ms: float | None = None  # tới byte đầu tiên của phản hồi
    first_token_ms: float | None = None  # tới chữ đầu tiên của kết quả (sau pha suy luận nếu có)
    reasoning_ms: float | None = None  # pha suy luận ẩn
    content_ms: float | None = None  # pha viết kết quả
    reasoning_tokens: int = 0
    cached_input_tokens: int = 0
    finish_reason: str | None = None  # stop | length | ...
    attempt: int = 1  # lần thử (bộ giới hạn đồng thời thử lại khi 429 hoặc hết giờ)
    queue_wait_ms: float | None = None  # chờ ở bộ giới hạn đồng thời trước khi gọi


class CallObservation(Protocol):
    """Lời gọi đang chạy được theo dõi bên ngoài (Langfuse): đóng bằng `finish` ngay sau khi gọi xong."""

    def finish(self, record: CallRecord, output: Any = None) -> None: ...


_observer: Callable[[str, str, str, Any], CallObservation | None] | None = None


def set_observer(observer: Callable[[str, str, str, Any], CallObservation | None] | None) -> None:
    global _observer
    _observer = observer


def observe_start(kind: str, model: str, input_value: Any) -> CallObservation | None:
    """Gọi TRƯỚC khi gửi yêu cầu để thời gian đo được là thời gian thật. Không bao giờ ném lỗi."""
    if _observer is None:
        return None
    try:
        return _observer(kind, model, _current().operation, input_value)
    except Exception:
        logger.warning("Không mở được theo dõi cuộc gọi dịch vụ ngoài.", exc_info=True)
        return None


_EMPTY_CONTEXT = CallContext()
_context: ContextVar[CallContext | None] = ContextVar("call_context", default=None)
_collectors: ContextVar[tuple[list[CallRecord], ...]] = ContextVar("call_collectors", default=())
_sink: Callable[[CallRecord], None] | None = None
_prices: dict[str, float] = {"llm_in": 0.0, "llm_out": 0.0, "embed_per_second": 0.0}


def _current() -> CallContext:
    return _context.get() or _EMPTY_CONTEXT


def current_job_id() -> int | None:
    """Mã việc nền đang chạy (nếu lời gọi nằm trong một job): dùng để xếp lời gọi vào nhóm "nền" của bộ giới hạn."""
    return _current().job_id


def set_sink(sink: Callable[[CallRecord], None] | None) -> None:
    global _sink
    _sink = sink


def set_prices(*, llm_input_per_million: float, llm_output_per_million: float, embedding_per_second: float) -> None:
    """Đơn giá ước tính (USD) lấy từ cấu hình; để 0 nếu chưa biết — chi phí khi đó hiện 0, không đoán."""
    _prices["llm_in"] = llm_input_per_million
    _prices["llm_out"] = llm_output_per_million
    _prices["embed_per_second"] = embedding_per_second


def estimate_cost(record: CallRecord) -> float:
    if record.kind == "llm":
        return (record.prompt_tokens * _prices["llm_in"] + record.completion_tokens * _prices["llm_out"]) / 1_000_000
    # Modal tính tiền theo thời gian GPU chạy (kể cả lúc khởi động nguội), nên chi phí embedding = số giây của lời gọi × giá mỗi giây.
    return record.latency_ms / 1000 * _prices["embed_per_second"]


@contextmanager
def call_context(*, operation: str, user_id: int | None = None, job_id: int | None = None) -> Iterator[None]:
    current = _current()
    token = _context.set(
        replace(
            current,
            operation=operation,
            user_id=user_id if user_id is not None else current.user_id,
            job_id=job_id if job_id is not None else current.job_id,
        )
    )
    try:
        yield
    finally:
        _context.reset(token)


def set_user_id(user_id: int) -> None:
    _context.set(replace(_current(), user_id=user_id))


def set_request_id(request_id: str) -> None:
    _context.set(replace(_current(), request_id=request_id))


@dataclass
class Collected:
    calls: list[CallRecord] = field(default_factory=list)

    @property
    def prompt_tokens(self) -> int:
        return sum(c.prompt_tokens for c in self.calls)

    @property
    def completion_tokens(self) -> int:
        return sum(c.completion_tokens for c in self.calls)

    @property
    def model(self) -> str | None:
        return self.calls[-1].model if self.calls else None

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)

    @property
    def latency_ms(self) -> float:
        return sum(c.latency_ms for c in self.calls)


@contextmanager
def collect_calls() -> Iterator[Collected]:
    collected = Collected()
    token = _collectors.set((*_collectors.get(), collected.calls))
    try:
        yield collected
    finally:
        _collectors.reset(token)


def emit(record: CallRecord, observation: CallObservation | None = None, output: Any = None) -> None:
    """Ghi nhận một lần gọi. Không bao giờ ném lỗi ra ngoài. `observation`/`output` chỉ đi tới bộ theo dõi, không vào DB."""
    try:
        ctx = _current()
        full = replace(
            record, operation=ctx.operation, user_id=ctx.user_id, request_id=ctx.request_id, job_id=ctx.job_id
        )
        full = replace(full, cost_usd=estimate_cost(full))
        for bucket in _collectors.get():
            bucket.append(full)
        if observation is not None:
            observation.finish(full, output)
        if _sink is not None:
            _sink(full)
    except Exception:
        logger.warning("Không ghi được số liệu cuộc gọi dịch vụ ngoài.", exc_info=True)
