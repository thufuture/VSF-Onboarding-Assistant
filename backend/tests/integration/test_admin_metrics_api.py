"""Số liệu LLM/embedding ghi vào `llm_calls` và màn "chi phí và hiệu năng" của Admin (mục 12, giai đoạn A)."""

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from viga_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    app,
    client_for,
    llm_holder,
    login,
    make_member,
    session_factory,
    team,
)

from src.infrastructure.observability.call_metrics import CallRecord
from src.model.llm_call import LlmCall
from src.services.portal.metrics_service import DbCallSink, get_metrics

pytestmark = pytest.mark.integration


def record(
    operation: str, latency: float, *, ok: bool = True, tokens: tuple[int, int] = (0, 0), cost: float = 0.0
) -> CallRecord:
    return CallRecord(
        kind="llm",
        provider="deepseek",
        model="deepseek-flash",
        latency_ms=latency,
        ok=ok,
        prompt_tokens=tokens[0],
        completion_tokens=tokens[1],
        error=None if ok else "network",
        operation=operation,
        cost_usd=cost,
    )


async def cleanup(factory: async_sessionmaker[AsyncSession], prefix: str) -> None:
    async with factory() as session:
        await session.execute(delete(LlmCall).where(LlmCall.operation.like(f"{prefix}%")))
        await session.commit()


async def test_sink_writes_one_row_per_call_without_any_content(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    operation = f"test.{uuid4().hex[:8]}"
    sink = DbCallSink(session_factory)

    sink(record(operation, 120.0, tokens=(2400, 300), cost=0.00108))
    await sink.drain()

    async with session_factory() as session:
        report = await get_metrics(session, days=1)
    row = next(o for o in report.operations if o.operation == operation)
    assert (row.calls, row.errors, row.prompt_tokens, row.completion_tokens) == (1, 0, 2400, 300)
    assert row.cost_usd == pytest.approx(0.00108)
    columns = {column.name for column in LlmCall.__table__.columns}
    assert columns.isdisjoint({"prompt", "content", "question", "answer", "text"})  # INV8
    await cleanup(session_factory, operation)


async def test_metrics_aggregate_percentiles_errors_tokens_and_cost(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    operation = f"test.{uuid4().hex[:8]}"
    sink = DbCallSink(session_factory)
    for latency in (100, 200, 300, 400, 500):
        sink(record(operation, latency, tokens=(1000, 100), cost=0.001))
    sink(record(operation, 900, ok=False))
    await sink.drain()

    async with session_factory() as session:
        report = await get_metrics(session, days=1)

    row = next(o for o in report.operations if o.operation == operation)
    assert row.calls == 6 and row.errors == 1
    assert row.p50_latency_ms == pytest.approx(350.0)  # trung vị của 100,200,300,400,500,900
    assert row.p95_latency_ms == pytest.approx(800.0)  # vị trí 4,75: nội suy giữa 500 và 900
    assert row.avg_latency_ms == pytest.approx(400.0)
    assert (row.prompt_tokens, row.completion_tokens) == (5000, 500)
    assert row.cost_usd == pytest.approx(0.005)
    assert report.calls >= 6 and report.cost_usd >= 0.005
    assert report.daily and report.daily[-1].calls >= 6
    await cleanup(session_factory, operation)


async def test_old_calls_fall_outside_the_window(session_factory: async_sessionmaker[AsyncSession]) -> None:
    from datetime import UTC, datetime, timedelta

    operation = f"test.{uuid4().hex[:8]}"
    async with session_factory() as session:
        session.add(
            LlmCall(
                kind="llm",
                operation=operation,
                provider="deepseek",
                model="m",
                latency_ms=10.0,
                ok=True,
                created_at=datetime.now(UTC) - timedelta(days=10),
            )
        )
        await session.commit()

    async with session_factory() as session:
        week = await get_metrics(session, days=7)
        month = await get_metrics(session, days=30)

    assert all(o.operation != operation for o in week.operations)
    assert any(o.operation == operation for o in month.operations)
    await cleanup(session_factory, operation)


async def test_only_admin_can_read_metrics(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    operation = f"test.{uuid4().hex[:8]}"
    sink = DbCallSink(session_factory)
    sink(record(operation, 250.0, tokens=(100, 10), cost=0.0002))
    await sink.drain()
    admin = await make_member("ADMIN", team.id)
    hr = await make_member("HR", team.id)
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, admin)
        response = await client.get("/api/v1/admin/metrics?days=7")
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["days"] == 7
        row = next(o for o in body["operations"] if o["operation"] == operation)
        assert row["calls"] == 1 and row["p50_latency_ms"] == pytest.approx(250.0)
        assert (await client.get("/api/v1/admin/metrics?days=0")).status_code == 422
        assert (await client.get("/api/v1/admin/metrics?days=91")).status_code == 422

    for outsider in (hr, employee):
        async with client_for(app) as client:
            await login(client, outsider)
            assert (await client.get("/api/v1/admin/metrics")).status_code == 403
    await cleanup(session_factory, operation)
