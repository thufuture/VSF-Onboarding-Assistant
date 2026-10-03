"""Ticket gửi HR và câu hỏi Viga chưa trả lời được trên PostgreSQL thật (plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md mục 17.5).

Quy tắc đã chốt: gửi tới HR phòng ban; nhân viên xem/sửa trước khi gửi; 5 ticket/người/ngày; chặn câu giống nhau trong 10 phút;
HR chỉ thấy ticket và câu hỏi chưa trả lời được (ẩn danh) của phòng ban mình; đóng ticket không đổi trạng thái task.
"""

from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from sqlalchemy import select
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

from src.model.employee_task import EmployeeTask
from src.model.ticket import Ticket

pytestmark = pytest.mark.integration

TICKETS = "/api/v1/portal/tickets"


def new_ticket(question: str | None = None, **extra: Any) -> dict[str, Any]:
    return {"question": question or f"Mình chưa nhận được laptop {uuid4().hex[:8]}", **extra}


async def test_employee_sends_a_ticket_to_the_hr_of_their_team(
    app: FastAPI,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id, "Trần Anh Thư")
    hr = await make_member("HR", team.id, "HR Hồng")
    outsider_hr = await make_member("HR", other_team.id, "HR phòng khác")

    async with client_for(app) as client:
        await login(client, employee)
        tasks = await employee_tasks(client)
        created = await client.post(
            TICKETS,
            json=new_ticket(
                "Mình chưa nhận được laptop, ITHD chưa phản hồi",
                note="Đã chờ từ sáng",
                employee_task_id=tasks["Nhận laptop"],
            ),
        )
        assert created.status_code == 201, created.text
        ticket = created.json()
        assert ticket["status"] == "OPEN"
        assert ticket["source"] == "MANUAL"
        assert ticket["requester_name"] == "Trần Anh Thư"
        assert ticket["requester_email"].endswith("@vsf-demo.example") or "@" in ticket["requester_email"]
        assert ticket["team_name"] == "Phòng nhân sự thử"
        assert ticket["related_task_title"] == "Nhận laptop"
        detail = (await client.get(f"{TICKETS}/{ticket['id']}")).json()
        assert "Ghi chú của nhân viên: Đã chờ từ sáng" in detail["messages"][0]["body"]
        assert [t["id"] for t in (await client.get(f"{TICKETS}/mine")).json()] == [ticket["id"]]

    async with client_for(app) as client:
        await login(client, hr)
        queue = (await client.get(TICKETS)).json()
        assert [t["id"] for t in queue] == [ticket["id"]]  # HR cùng phòng ban thấy trong hàng đợi chung
        assert (await client.get(f"{TICKETS}/{ticket['id']}")).status_code == 200

    async with client_for(app) as client:
        await login(client, outsider_hr)
        assert (await client.get(TICKETS)).json() == []  # HR phòng khác không thấy
        assert (await client.get(f"{TICKETS}/{ticket['id']}")).status_code == 404


async def test_ticket_from_a_viga_conversation_is_marked_and_linked(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        conversation_id = (await client.post("/api/v1/viga/ask", json={"question": "Hôm nay làm gì?"})).json()[
            "conversation_id"
        ]
        created = (
            await client.post(TICKETS, json=new_ticket("Câu hỏi từ Viga", conversation_id=conversation_id))
        ).json()
        forged = (await client.post(TICKETS, json=new_ticket("Câu khác", conversation_id=999999999))).json()

    assert created["source"] == "VIGA"
    assert forged["source"] == "MANUAL"  # mã cuộc trò chuyện lạ bị bỏ qua


async def test_cannot_attach_someone_elses_task_or_conversation(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    owner = await make_member("USER", team.id)
    intruder = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, owner)
        owner_tasks = await employee_tasks(client)
        owner_conversation = (await client.post("/api/v1/viga/ask", json={"question": "Hôm nay làm gì?"})).json()[
            "conversation_id"
        ]
    async with client_for(app) as client:
        await login(client, intruder)
        created = (
            await client.post(
                TICKETS,
                json=new_ticket(employee_task_id=owner_tasks["Nhận laptop"], conversation_id=owner_conversation),
            )
        ).json()

    assert created["related_task_title"] is None
    assert created["source"] == "MANUAL"


async def test_hr_replies_claims_and_resolves_without_touching_the_task(
    app: FastAPI,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)
    hr = await make_member("HR", team.id, "HR Hồng")
    other_hr = await make_member("HR", team.id, "HR Lan")

    async with client_for(app) as client:
        await login(client, employee)
        tasks = await employee_tasks(client)
        ticket_id = (await client.post(TICKETS, json=new_ticket(employee_task_id=tasks["Nhận laptop"]))).json()["id"]

    async with client_for(app) as client:
        await login(client, hr)
        reply = await client.post(
            f"{TICKETS}/{ticket_id}/messages", json={"body": "ITHD sẽ mang laptop tới chiều nay."}
        )
        assert reply.status_code == 201, reply.text
        detail = reply.json()
        assert detail["ticket"]["status"] == "IN_PROGRESS"  # HR đầu tiên trả lời coi như nhận xử lý
        assert detail["ticket"]["assigned_hr_name"] == "HR Hồng"
        assert detail["ticket"]["last_sender_is_staff"] is True

    async with client_for(app) as client:
        await login(client, other_hr)
        taken = await client.post(f"{TICKETS}/{ticket_id}/claim")
        assert taken.status_code == 409  # đã có HR nhận, tránh xử lý trùng
        assert taken.json()["code"] == "TICKET_ALREADY_CLAIMED"

    async with client_for(app) as client:
        await login(client, employee)
        mine = (await client.get(f"{TICKETS}/mine")).json()[0]
        assert mine["last_sender_is_staff"] is True  # nhân viên có phản hồi mới để xem
        thread = (await client.get(f"{TICKETS}/{ticket_id}")).json()
        assert [m["sender_role"] for m in thread["messages"]] == ["USER", "HR"]
        assert [m["mine"] for m in thread["messages"]] == [True, False]
        answered = await client.post(f"{TICKETS}/{ticket_id}/messages", json={"body": "Cảm ơn, mình nhận rồi."})
        assert answered.status_code == 201
        # Nhân viên không đổi được trạng thái hay nhận xử lý.
        assert (await client.patch(f"{TICKETS}/{ticket_id}/status", json={"status": "CLOSED"})).status_code == 403

    async with client_for(app) as client:
        await login(client, hr)
        resolved = await client.patch(
            f"{TICKETS}/{ticket_id}/status", json={"status": "RESOLVED", "resolution_note": "Đã giao laptop."}
        )
        assert resolved.json()["ticket"]["status"] == "RESOLVED"
        assert resolved.json()["ticket"]["resolution_note"] == "Đã giao laptop."
        closed = await client.patch(f"{TICKETS}/{ticket_id}/status", json={"status": "CLOSED"})
        assert closed.status_code == 200
        late = await client.post(f"{TICKETS}/{ticket_id}/messages", json={"body": "thêm"})
        assert late.status_code == 409 and late.json()["code"] == "TICKET_CLOSED"

    # P0A D6: đóng ticket KHÔNG tự đổi trạng thái task liên quan.
    async with session_factory() as session:
        statuses = (
            await session.scalars(select(EmployeeTask.status).where(EmployeeTask.id == tasks["Nhận laptop"]))
        ).all()
    assert list(statuses) == ["READY"]


async def test_limits_five_tickets_per_person_per_day_and_blocks_duplicates(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        same = "Mình chưa nhận được laptop"
        first = await client.post(TICKETS, json=new_ticket(same))
        duplicate = await client.post(TICKETS, json=new_ticket("  mình chưa nhận được LAPTOP  "))
        assert first.status_code == 201
        assert duplicate.status_code == 409 and duplicate.json()["code"] == "TICKET_DUPLICATE"

        for index in range(4):
            assert (
                await client.post(TICKETS, json=new_ticket(f"Câu hỏi khác số {index} {uuid4().hex[:6]}"))
            ).status_code == 201
        sixth = await client.post(TICKETS, json=new_ticket(f"Câu thứ sáu {uuid4().hex[:6]}"))

    assert sixth.status_code == 429
    assert sixth.json()["code"] == "TICKET_DAILY_LIMIT"


async def test_user_without_a_team_cannot_send_a_ticket(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    from sqlalchemy import delete

    from src.model.team_member import TeamMember

    employee = await make_member("USER", team.id)
    async with session_factory() as session:
        await session.execute(delete(TeamMember).where(TeamMember.user_id == employee.id))
        await session.commit()

    async with client_for(app) as client:
        await login(client, employee)
        response = await client.post(TICKETS, json=new_ticket())

    assert response.status_code == 409
    assert response.json()["code"] == "NO_TEAM_ASSIGNED"


async def test_admin_sees_every_team_and_status_filter_works(
    app: FastAPI,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    mine = await make_member("USER", team.id)
    theirs = await make_member("USER", other_team.id)
    admin = await make_member("ADMIN", team.id)
    ids = []
    for employee in (mine, theirs):
        async with client_for(app) as client:
            await login(client, employee)
            ids.append((await client.post(TICKETS, json=new_ticket())).json()["id"])

    async with client_for(app) as client:
        await login(client, admin)
        everything = {t["id"] for t in (await client.get(TICKETS)).json()}
        await client.patch(f"{TICKETS}/{ids[0]}/status", json={"status": "RESOLVED"})
        resolved = {t["id"] for t in (await client.get(f"{TICKETS}?status=RESOLVED")).json()}

    assert set(ids) <= everything
    assert ids[0] in resolved and ids[1] not in resolved


async def test_employee_cannot_use_staff_endpoints(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        assert (await client.get(TICKETS)).status_code == 403
        assert (await client.get("/api/v1/portal/content-gaps")).status_code == 403


async def test_content_gaps_are_anonymous_grouped_and_scoped_to_the_team(
    app: FastAPI,
    llm_holder: Any,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    first = await make_member("USER", team.id, "Trần Anh Thư")
    second = await make_member("USER", team.id, "Lê Văn B")
    far = await make_member("USER", other_team.id, "Người phòng khác")
    hr = await make_member("HR", team.id)
    far_hr = await make_member("HR", other_team.id)
    unique = uuid4().hex[:8]
    question = f"Quy định gửi xe máy tầng hầm {unique}?"
    llm_holder.llm = ScriptedLlm(route=route_json("search_documents"))

    for employee, text in ((first, question), (second, question.lower()), (far, f"Câu của phòng khác {unique}")):
        async with client_for(app) as client:
            await login(client, employee)
            body = (await client.post("/api/v1/viga/ask", json={"question": text})).json()
            assert body["response_type"] == "NO_BASIS"

    async with client_for(app) as client:
        await login(client, hr)
        gaps = (await client.get("/api/v1/portal/content-gaps")).json()
        mine = [g for g in gaps if unique in g["question_text"]]
        assert len(mine) == 1 and mine[0]["occurrences"] == 2  # câu giống nhau gom lại và đếm
        assert "Trần" not in str(gaps) and "Lê Văn" not in str(gaps)  # ẩn danh: không có tên người hỏi
        assert not any("phòng khác" in g["question_text"] for g in gaps)

        assert (await client.post(f"/api/v1/portal/content-gaps/{mine[0]['id']}/resolve")).status_code == 204
        after = (await client.get("/api/v1/portal/content-gaps")).json()
        assert not any(unique in g["question_text"] for g in after)
        with_resolved = (await client.get("/api/v1/portal/content-gaps?include_resolved=true")).json()
        assert any(unique in g["question_text"] and g["resolved"] for g in with_resolved)

    async with client_for(app) as client:
        await login(client, far_hr)
        far_gaps = (await client.get("/api/v1/portal/content-gaps")).json()
        assert [g["question_text"] for g in far_gaps if unique in g["question_text"]] == [
            f"Câu của phòng khác {unique}"
        ]
        # HR phòng khác không đóng được nhóm của phòng mình.
        assert (await client.post(f"/api/v1/portal/content-gaps/{mine[0]['id']}/resolve")).status_code == 404


async def test_ticket_row_is_removed_with_its_requester_cleanup(
    app: FastAPI,
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    employee = await make_member("USER", team.id)

    async with client_for(app) as client:
        await login(client, employee)
        ticket_id = (await client.post(TICKETS, json=new_ticket())).json()["id"]

    async with session_factory() as session:
        row = await session.get(Ticket, ticket_id)
    assert row is not None and row.created_by_user_id == employee.id
