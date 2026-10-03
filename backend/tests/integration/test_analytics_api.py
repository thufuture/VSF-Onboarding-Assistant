"""Số liệu trang Tổng quan (biểu đồ đường, cột, tròn, chi phí, độ trễ) trên PostgreSQL thật.

HR chỉ thấy phòng ban của mình (nhân viên, task, ticket, câu hỏi chưa trả lời được, chi phí và độ trễ AI của người trong phòng ban);
Admin thấy tất cả. Chỉ số liệu tổng hợp, không có nội dung hay câu hỏi của từng người.
"""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from viga_fixtures import (  # noqa: F401  (fixture được pytest tìm theo tên trong module này)
    MakeMember,
    ScriptedLlm,
    app,
    client_for,
    employee_tasks,
    llm_holder,
    login,
    make_member,
    other_team,
    published_template,
    route_json,
    session_factory,
    team,
)

from src.model.job import Job
from src.model.llm_call import LlmCall
from src.services.ingest.ingest_service import today_in

pytestmark = pytest.mark.integration

URL = "/api/v1/portal/analytics"


def keyed(items: list[dict[str, Any]]) -> dict[str, int]:
    return {item["key"]: item["count"] for item in items}


async def seed_ai(
    factory: async_sessionmaker[AsyncSession], hr_id: int, outsider_id: int
) -> tuple[list[int], list[int]]:
    """Một lượt tạo task (2 lời gọi LLM), một lượt kích hoạt (1 lời gọi embedding) của HR và vài lời gọi của người phòng khác."""
    now = datetime.now(UTC)
    async with factory() as session:
        task_job = Job(
            kind="AI_TASK_PROPOSAL",
            status="SUCCEEDED",
            payload={"version_ids": [1, 2]},
            idempotency_key=f"analytics-{uuid4().hex}",
            created_by=hr_id,
            started_at=now - timedelta(seconds=40),
            finished_at=now - timedelta(seconds=10),
            progress_percent=100,
            result={"documents": [{"proposals": [{}, {}, {}]}, {"proposals": [{}]}]},
        )
        activation_job = Job(
            kind="ACTIVATE_VERSION",
            status="SUCCEEDED",
            payload={"version_id": 1},
            idempotency_key=f"analytics-{uuid4().hex}",
            created_by=hr_id,
            started_at=now - timedelta(seconds=9),
            finished_at=now - timedelta(seconds=4),
            progress_percent=100,
            result={"chunk_count": 18, "section_count": 18},
        )
        failed_job = Job(
            kind="AI_TASK_PROPOSAL",
            status="FAILED",
            payload={"version_ids": [3]},
            idempotency_key=f"analytics-{uuid4().hex}",
            created_by=hr_id,
            started_at=now - timedelta(seconds=3),
            finished_at=now - timedelta(seconds=2),
            result=None,
        )
        outsider_job = Job(
            kind="AI_TASK_PROPOSAL",
            status="SUCCEEDED",
            payload={"version_ids": [9]},
            idempotency_key=f"analytics-{uuid4().hex}",
            created_by=outsider_id,
            started_at=now - timedelta(seconds=5),
            finished_at=now - timedelta(seconds=1),
            result={"documents": [{"proposals": [{}]}]},
        )
        session.add_all([task_job, activation_job, failed_job, outsider_job])
        await session.flush()

        def call(**fields: Any) -> LlmCall:
            base: dict[str, Any] = {"kind": "llm", "provider": "deepseek", "model": "deepseek-flash", "ok": True}
            return LlmCall(**{**base, **fields})

        session.add_all(
            [
                call(
                    operation="task.proposal",
                    latency_ms=20000,
                    prompt_tokens=2000,
                    completion_tokens=9000,
                    cost_usd=0.0114,
                    user_id=hr_id,
                    job_id=task_job.id,
                ),
                call(
                    operation="task.proposal",
                    latency_ms=8000,
                    prompt_tokens=500,
                    completion_tokens=3000,
                    cost_usd=0.0038,
                    user_id=hr_id,
                    job_id=task_job.id,
                ),
                call(
                    kind="embedding",
                    operation="ingest.embed",
                    provider="modal",
                    latency_ms=3300,
                    input_count=18,
                    cost_usd=0.0,
                    user_id=hr_id,
                    job_id=activation_job.id,
                ),
                call(
                    operation="chat.answer",
                    latency_ms=1700,
                    prompt_tokens=6800,
                    completion_tokens=290,
                    cost_usd=0.0024,
                    user_id=hr_id,
                ),
                call(operation="chat.answer", latency_ms=900, ok=False, cost_usd=0.0, user_id=hr_id),
                # Người phòng khác: HR của phòng này không được thấy; Admin thấy.
                call(
                    operation="task.proposal",
                    latency_ms=1000,
                    prompt_tokens=10,
                    completion_tokens=10,
                    cost_usd=0.5,
                    user_id=outsider_id,
                    job_id=outsider_job.id,
                ),
            ]
        )
        await session.commit()
        return (
            [task_job.id, activation_job.id, failed_job.id],
            [outsider_job.id],
        )


async def cleanup_ai(factory: async_sessionmaker[AsyncSession], job_ids: list[int], user_ids: list[int]) -> None:
    async with factory() as session:
        await session.execute(delete(LlmCall).where(LlmCall.job_id.in_(job_ids)))
        await session.execute(delete(LlmCall).where(LlmCall.user_id.in_(user_ids)))
        await session.execute(delete(Job).where(Job.id.in_(job_ids)))
        await session.commit()


async def test_hr_overview_is_scoped_to_their_team_and_adds_up(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    hr_far = await make_member("HR", other_team.id)
    alice = await make_member("USER", team.id)
    bob = await make_member("USER", team.id)
    carol = await make_member("USER", other_team.id)
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))
    unique = uuid4().hex[:8]

    async with client_for(app) as client:
        await login(client, alice)
        tasks = await employee_tasks(client)
        assert (await client.post(f"/api/v1/portal/me/tasks/{tasks['Nhận laptop']}/complete")).status_code == 200
        await client.post("/api/v1/viga/ask", json={"question": "Hôm nay làm gì?"})
        await client.post("/api/v1/viga/ask", json={"question": "Mentor của mình là ai?"})
        await client.post("/api/v1/viga/ask", json={"question": f"Quy định gửi xe máy tầng hầm {unique}?"})
        assert (
            await client.post("/api/v1/portal/tickets", json={"question": f"Chưa nhận laptop {unique}"})
        ).status_code == 201
    async with client_for(app) as client:
        await login(client, bob)
        await employee_tasks(client)
    async with client_for(app) as client:
        await login(client, carol)  # phòng khác, chưa có lộ trình
        await client.post("/api/v1/viga/ask", json={"question": "Hôm nay làm gì?"})
        await client.post("/api/v1/portal/tickets", json={"question": f"Câu của phòng khác {unique}"})

    task_jobs, outsider_jobs = await seed_ai(session_factory, hr.id, hr_far.id)
    try:
        async with client_for(app) as client:
            await login(client, hr)
            body = (await client.get(f"{URL}?days=7")).json()
            await client.post(  # HR trả lời ticket của nhân viên cùng phòng để có "phản hồi đầu tiên"
                f"/api/v1/portal/tickets/{(await client.get('/api/v1/portal/tickets')).json()[0]['id']}/messages",
                json={"body": "Đã nhận, mang máy lên chiều nay."},
            )
            body_after = (await client.get(f"{URL}?days=7")).json()

        # Khung thời gian và phạm vi
        assert body["days"] == 7 and len(body["dates"]) == 7
        assert body["dates"][-1] == today_in().isoformat()
        assert body["scope"] == "TEAM" and body["team_name"] == "Phòng nhân sự thử"

        # Nhân viên và tiến độ: chỉ alice và bob (carol thuộc phòng khác)
        people = body["people"]
        assert people["employees_total"] == 2
        assert keyed(people["by_progress"]) == {"NO_JOURNEY": 0, "NOT_STARTED": 1, "IN_PROGRESS": 1, "COMPLETED": 0}
        assert keyed(people["tasks_by_state"]) == {"done": 1, "ready": 4, "locked": 3}
        assert people["completion_percent"] == 12
        assert people["tasks_by_group"] == [{"group": "NONE", "done": 1, "ready": 4, "locked": 3}]
        assert people["completed_per_day"] == [0, 0, 0, 0, 0, 0, 1]

        # Viga: ba câu của alice (carol không tính), tỉ lệ không tốn LLM và câu có nội dung trả lời
        viga = body["viga"]
        assert viga["total_questions"] == 3
        assert viga["questions_per_day"][-1] == 3 and sum(viga["questions_per_day"]) == 3
        assert keyed(viga["by_outcome"])["DAY_PLAN"] == 1
        assert keyed(viga["by_outcome"])["OUT_OF_SCOPE"] == 1
        assert keyed(viga["by_outcome"])["NO_BASIS"] == 1
        assert keyed(viga["by_route"]) == {"SHORTCUT": 1, "GUARD": 1, "LLM": 1, "FALLBACK": 0}
        assert viga["no_llm_percent"] == 67  # 2 trên 3 câu không gọi LLM
        assert viga["answered_percent"] == 33

        # Ticket và câu chưa trả lời được: chỉ của phòng này
        tickets = body["tickets"]
        assert keyed(tickets["by_status"]) == {"OPEN": 1, "IN_PROGRESS": 0, "RESOLVED": 0, "CLOSED": 0}
        assert tickets["created_per_day"][-1] == 1
        assert tickets["open_gaps"] == 1
        assert tickets["avg_first_reply_hours"] is None
        assert body_after["tickets"]["avg_first_reply_hours"] is not None
        assert body_after["tickets"]["avg_first_reply_hours"] >= 0
        assert keyed(body_after["tickets"]["by_status"])["IN_PROGRESS"] == 1

        # Tài liệu: đủ sáu trạng thái, luôn có khóa
        assert [item["key"] for item in body["documents"]["by_state"]] == [
            "CURRENT",
            "SCHEDULED",
            "DRAFT",
            "PROCESSING",
            "SUPERSEDED",
            "FAILED",
        ]

        # AI: chỉ lời gọi của người trong phòng (loại 0,5 USD của phòng khác)
        ai = body["ai"]
        assert ai["calls"] == 5 and ai["errors"] == 1
        assert ai["cost_usd"] == pytest.approx(0.0176)
        assert ai["calls_per_day"][-1] == 5 and ai["errors_per_day"][-1] == 1
        assert ai["cost_per_day"][-1] == pytest.approx(0.0176)
        operations = {row["operation"]: row for row in ai["by_operation"]}
        assert [row["operation"] for row in ai["by_operation"]][0] == "task.proposal"  # xếp theo chi phí giảm dần
        assert operations["task.proposal"]["calls"] == 2
        assert operations["task.proposal"]["p50_latency_ms"] == pytest.approx(14000.0)
        assert operations["task.proposal"]["completion_tokens"] == 12000
        assert operations["chat.answer"]["errors"] == 1
        assert operations["ingest.embed"]["input_count"] == 18

        # Từng lượt: thời gian chạy thật, chi phí và độ trễ LLM cộng theo job
        runs = {run["job_id"]: run for run in ai["task_runs"]}
        ok_run = runs[task_jobs[0]]
        assert ok_run["status"] == "SUCCEEDED"
        assert ok_run["duration_seconds"] == pytest.approx(30.0, abs=0.01)
        assert (ok_run["documents"], ok_run["items"], ok_run["llm_calls"]) == (2, 4, 2)
        assert ok_run["llm_latency_ms"] == pytest.approx(28000.0)
        assert ok_run["cost_usd"] == pytest.approx(0.0152)
        assert (ok_run["prompt_tokens"], ok_run["completion_tokens"]) == (2500, 12000)
        failed = runs[task_jobs[2]]
        assert failed["status"] == "FAILED" and failed["items"] == 0 and failed["llm_calls"] == 0
        assert outsider_jobs[0] not in runs  # lượt của phòng khác không hiện
        assert [run["job_id"] for run in ai["task_runs"]] == sorted(
            run["job_id"] for run in ai["task_runs"]
        )  # cũ trước mới sau
        (activation,) = ai["activation_runs"]
        assert activation["job_id"] == task_jobs[1]
        assert (activation["documents"], activation["items"], activation["llm_calls"]) == (1, 18, 1)
        assert activation["duration_seconds"] == pytest.approx(5.0, abs=0.01)
    finally:
        await cleanup_ai(session_factory, task_jobs + outsider_jobs, [hr.id, hr_far.id])


async def test_admin_sees_every_team_including_other_teams_ai_cost(
    app: FastAPI,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    hr = await make_member("HR", team.id)
    hr_far = await make_member("HR", other_team.id)
    admin = await make_member("ADMIN", team.id)
    task_jobs, outsider_jobs = await seed_ai(session_factory, hr.id, hr_far.id)
    try:
        async with client_for(app) as client:
            await login(client, admin)
            body = (await client.get(f"{URL}?days=14")).json()

        assert body["scope"] == "ALL" and body["team_name"] is None and len(body["dates"]) == 14
        assert body["ai"]["cost_usd"] >= 0.5176  # gồm cả 0,5 USD của phòng khác
        assert outsider_jobs[0] in {run["job_id"] for run in body["ai"]["task_runs"]}
    finally:
        await cleanup_ai(session_factory, task_jobs + outsider_jobs, [hr.id, hr_far.id])


async def test_hr_without_a_team_gets_zeros_not_an_error(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    from src.model.team_member import TeamMember

    hr = await make_member("HR", team.id)
    async with session_factory() as session:
        await session.execute(delete(TeamMember).where(TeamMember.user_id == hr.id))
        await session.commit()

    async with client_for(app) as client:
        await login(client, hr)
        response = await client.get(f"{URL}?days=7")

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["people"]["employees_total"] == 0 and body["ai"]["calls"] == 0 and body["viga"]["total_questions"] == 0
    assert body["tickets"]["created_per_day"] == [0] * 7 and body["ai"]["cost_per_day"] == [0.0] * 7


async def test_only_staff_can_read_analytics_and_days_is_validated(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    employee = await make_member("USER", team.id)
    hr = await make_member("HR", team.id)

    async with client_for(app) as client:
        assert (await client.get(URL)).status_code == 401
        await login(client, employee)
        assert (await client.get(URL)).status_code == 403
    async with client_for(app) as client:
        await login(client, hr)
        assert (await client.get(f"{URL}?days=0")).status_code == 422
        assert (await client.get(f"{URL}?days=91")).status_code == 422
        assert len((await client.get(URL)).json()["dates"]) == 14  # mặc định 14 ngày
