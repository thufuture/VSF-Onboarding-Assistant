"""Ghi và tổng hợp số liệu gọi LLM/embedding (`llm_calls`): số lượt, lỗi, độ trễ p50/p95, token, chi phí ước tính.

Chỉ có số liệu, không có nội dung (INV8). Ghi bản ghi chạy nền (fire-and-forget, phiên DB riêng) để không làm chậm hay
làm hỏng câu trả lời; lỗi ghi chỉ được log.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.infrastructure.observability.call_metrics import CallRecord
from src.model.llm_call import LLM_COST, LlmCall

logger = logging.getLogger(__name__)


class DbCallSink:
    """Nơi nhận `CallRecord` từ adapter: ghi một dòng `llm_calls` bằng phiên DB riêng, không chặn luồng chính."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory
        self._tasks: set[asyncio.Task[None]] = set()

    def __call__(self, record: CallRecord) -> None:
        try:
            task = asyncio.get_running_loop().create_task(self._write(record))
        except RuntimeError:  # không có vòng lặp sự kiện (gọi ngoài ngữ cảnh async): bỏ qua, đo lường không bắt buộc
            return
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def drain(self) -> None:
        """Chờ các bản ghi đang ghi dở (dùng khi tắt ứng dụng và trong test)."""
        if self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)

    async def _write(self, record: CallRecord) -> None:
        try:
            async with self._session_factory() as session:
                session.add(
                    LlmCall(
                        kind=record.kind,
                        operation=record.operation,
                        provider=record.provider,
                        model=record.model[:64],
                        latency_ms=record.latency_ms,
                        ok=record.ok,
                        error=record.error,
                        prompt_tokens=record.prompt_tokens,
                        completion_tokens=record.completion_tokens,
                        input_count=record.input_count,
                        cost_usd=record.cost_usd,
                        user_id=record.user_id,
                        request_id=record.request_id,
                        job_id=record.job_id,
                        first_byte_ms=record.first_byte_ms,
                        first_token_ms=record.first_token_ms,
                        reasoning_ms=record.reasoning_ms,
                        content_ms=record.content_ms,
                        reasoning_tokens=record.reasoning_tokens,
                        cached_input_tokens=record.cached_input_tokens,
                        finish_reason=record.finish_reason,
                        attempt=record.attempt,
                        queue_wait_ms=record.queue_wait_ms,
                    )
                )
                await session.commit()
        except Exception:
            logger.warning("Không ghi được llm_calls.", exc_info=True)


@dataclass
class OperationMetrics:
    operation: str
    kind: str
    calls: int
    errors: int
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    input_count: int
    cost_usd: float


@dataclass
class DailyCost:
    day: str
    calls: int
    cost_usd: float


@dataclass
class MetricsReport:
    days: int
    since: datetime
    calls: int
    errors: int
    cost_usd: float
    operations: list[OperationMetrics]
    daily: list[DailyCost]


async def get_metrics(session: AsyncSession, *, days: int) -> MetricsReport:
    since = datetime.now(UTC) - timedelta(days=days)
    errors = func.sum(case((LlmCall.ok.is_(False), 1), else_=0))
    rows = (
        await session.execute(
            select(
                LlmCall.operation,
                LlmCall.kind,
                func.count(),
                errors,
                func.avg(LlmCall.latency_ms),
                func.percentile_cont(0.5).within_group(LlmCall.latency_ms),
                func.percentile_cont(0.95).within_group(LlmCall.latency_ms),
                func.coalesce(func.sum(LlmCall.prompt_tokens), 0),
                func.coalesce(func.sum(LlmCall.completion_tokens), 0),
                func.coalesce(func.sum(LlmCall.input_count), 0),
                func.coalesce(func.sum(LLM_COST), 0.0),
            )
            .where(LlmCall.created_at >= since)
            .group_by(LlmCall.operation, LlmCall.kind)
            .order_by(LlmCall.operation)
        )
    ).all()
    operations = [
        OperationMetrics(
            operation=op,
            kind=kind,
            calls=int(calls),
            errors=int(errs or 0),
            avg_latency_ms=float(avg or 0),
            p50_latency_ms=float(p50 or 0),
            p95_latency_ms=float(p95 or 0),
            prompt_tokens=int(pt),
            completion_tokens=int(ct),
            input_count=int(ic),
            cost_usd=float(cost),
        )
        for op, kind, calls, errs, avg, p50, p95, pt, ct, ic, cost in rows
    ]
    day = func.date_trunc("day", LlmCall.created_at)
    daily_rows = (
        await session.execute(
            select(day, func.count(), func.coalesce(func.sum(LLM_COST), 0.0))
            .where(LlmCall.created_at >= since)
            .group_by(day)
            .order_by(day)
        )
    ).all()
    return MetricsReport(
        days=days,
        since=since,
        calls=sum(o.calls for o in operations),
        errors=sum(o.errors for o in operations),
        cost_usd=sum(o.cost_usd for o in operations),
        operations=operations,
        daily=[DailyCost(day=d.date().isoformat(), calls=int(n), cost_usd=float(c)) for d, n, c in daily_rows],
    )
