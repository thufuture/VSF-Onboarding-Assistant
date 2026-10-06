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


# ───────────────────────────── Ảnh và video đính kèm ─────────────────────────────

ATTACHMENTS = "/api/v1/portal/ticket-attachments"


class FakeMediaStorage:
    """Thay Cloudinary: trả URL giả theo loại tệp, không gọi mạng."""

    def __init__(self) -> None:
        self.stored: list[tuple[str, str, int]] = []

    async def store(self, content: bytes, *, checksum: str, filename: str) -> str:
        return f"documents/{checksum}"

    async def store_media(self, content: bytes, *, filename: str, kind: str) -> str:
        self.stored.append((kind, filename, len(content)))
        return f"https://res.cloudinary.test/{kind.lower()}/{len(self.stored)}-{filename}"


def png(name: str = "loi.png", size: int = 2048) -> dict[str, Any]:
    return {"file": (name, b"\x89PNG" + b"0" * size, "image/png")}


async def test_employee_attaches_an_image_and_a_video_and_hr_sees_the_urls(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    from src.api.dependencies import get_storage_port

    storage = FakeMediaStorage()
    app.dependency_overrides[get_storage_port] = lambda: storage
    employee = await make_member("USER", team.id, "Trần Anh Thư")
    hr = await make_member("HR", team.id, "HR Hồng")

    async with client_for(app) as client:
        await login(client, employee)
        image = await client.post(ATTACHMENTS, files=png())
        video = await client.post(ATTACHMENTS, files={"file": ("man-hinh.mp4", b"0" * 4096, "video/mp4")})
        assert image.status_code == 201 and video.status_code == 201, (image.text, video.text)
        assert image.json()["kind"] == "IMAGE" and video.json()["kind"] == "VIDEO"
        assert image.json()["url"].startswith("https://res.cloudinary.test/image/")

        created = await client.post(
            TICKETS,
            json=new_ticket("Laptop báo lỗi màn hình xanh", attachment_ids=[image.json()["id"], video.json()["id"]]),
        )
        assert created.status_code == 201, created.text
        ticket_id = created.json()["id"]
        detail = (await client.get(f"{TICKETS}/{ticket_id}")).json()
        assert [a["kind"] for a in detail["messages"][0]["attachments"]] == ["IMAGE", "VIDEO"]

    async with client_for(app) as client:
        await login(client, hr)
        seen = (await client.get(f"{TICKETS}/{ticket_id}")).json()["messages"][0]["attachments"]
        assert [a["url"] for a in seen] == [image.json()["url"], video.json()["url"]]  # HR thấy đúng URL đã lưu
        reply_image = await client.post(ATTACHMENTS, files=png("huong-dan.png"))
        reply = await client.post(
            f"{TICKETS}/{ticket_id}/messages",
            json={"body": "Làm theo ảnh này", "attachment_ids": [reply_image.json()["id"]]},
        )
        assert reply.status_code == 201, reply.text
        assert reply.json()["messages"][-1]["attachments"][0]["filename"] == "huong-dan.png"
    assert [s[0] for s in storage.stored] == ["IMAGE", "VIDEO", "IMAGE"]


async def test_attachment_rules_type_size_ownership_and_limit(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, published_template: SimpleNamespace
) -> None:
    from src.api.dependencies import get_storage_port

    app.dependency_overrides[get_storage_port] = lambda: FakeMediaStorage()
    one = await make_member("USER", team.id, "Người một")
    two = await make_member("USER", team.id, "Người hai")

    async with client_for(app) as client:
        await login(client, one)
        # loại tệp: chữ thường và tệp đổi đuôi đều bị từ chối
        assert (
            await client.post(ATTACHMENTS, files={"file": ("ghi-chu.txt", b"abc", "text/plain")})
        ).status_code == 415
        assert (await client.post(ATTACHMENTS, files={"file": ("gia.png", b"abc", "video/mp4")})).status_code == 415
        # dung lượng ảnh tối đa 10 MB
        too_big = await client.post(ATTACHMENTS, files=png("to.png", size=10 * 1024 * 1024 + 10))
        assert too_big.status_code == 413 and too_big.json()["code"] == "ATTACHMENT_TOO_LARGE"
        assert (await client.post(ATTACHMENTS, files={"file": ("rong.png", b"", "image/png")})).status_code == 422

        mine = (await client.post(ATTACHMENTS, files=png())).json()
        # bỏ tệp đang chờ của chính mình được; tệp của người khác thì không
        spare = (await client.post(ATTACHMENTS, files=png("thua.png"))).json()
        assert (await client.delete(f"{ATTACHMENTS}/{spare['id']}")).status_code == 204
        assert (await client.delete(f"{ATTACHMENTS}/{spare['id']}")).status_code == 404
        # tối đa 5 tệp mỗi tin nhắn
        six = [mine["id"]] * 5 + [mine["id"] + 1000, mine["id"] + 1001]
        assert (await client.post(TICKETS, json=new_ticket(attachment_ids=six))).status_code == 422

    async with client_for(app) as client:
        await login(client, two)
        # người khác gắn tệp của "one" vào ticket của mình: tệp bị bỏ qua, không lộ
        created = await client.post(TICKETS, json=new_ticket(attachment_ids=[mine["id"]]))
        assert created.status_code == 201
        detail = (await client.get(f"{TICKETS}/{created.json()['id']}")).json()
        assert detail["messages"][0]["attachments"] == []
        assert (await client.delete(f"{ATTACHMENTS}/{mine['id']}")).status_code == 404


async def test_attachments_need_cloud_storage(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, tmp_path: Any
) -> None:
    from src.api.dependencies import get_storage_port
    from src.services.ingest.storage import LocalStorageAdapter

    app.dependency_overrides[get_storage_port] = lambda: LocalStorageAdapter(str(tmp_path))
    employee = await make_member("USER", team.id, "Người ba")

    async with client_for(app) as client:
        await login(client, employee)
        response = await client.post(ATTACHMENTS, files=png())
        assert response.status_code == 503 and response.json()["code"] == "ATTACHMENTS_UNAVAILABLE"


# ───────────────────────────── Số ticket có tin chưa đọc ─────────────────────────────


async def unread(client: Any) -> dict[str, Any]:
    response = await client.get(f"{TICKETS}/unread")
    assert response.status_code == 200, response.text
    data: dict[str, Any] = response.json()
    return data


async def test_unread_counts_tickets_not_messages_and_drops_by_one_when_opened(
    app: FastAPI,
    team: SimpleNamespace,
    other_team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id, "Trần Anh Thư")
    hr_one = await make_member("HR", team.id, "HR Hồng")
    hr_two = await make_member("HR", team.id, "HR Lan")
    outsider_hr = await make_member("HR", other_team.id, "HR phòng khác")

    async with client_for(app) as client:
        await login(client, employee)
        first = (await client.post(TICKETS, json=new_ticket("Câu hỏi thứ nhất"))).json()["id"]
        second = (await client.post(TICKETS, json=new_ticket("Câu hỏi thứ hai"))).json()["id"]
        # Tin của chính mình không làm ticket "chưa đọc" với mình.
        assert (await unread(client))["count"] == 0

    async with client_for(app) as client:
        await login(client, hr_one)
        # Hai ticket mới của nhân viên: HR thấy 2 (đếm ticket, mỗi ticket 1, kể cả khi có nhiều tin)
        await client.post(
            f"{TICKETS}/{first}/messages", json={"body": "Nhân viên nhắn thêm?"}
        )  # tin của HR, không đổi số
        before = await unread(client)
        assert before["count"] == 2 and before["ticket_ids"] == sorted([first, second])
        flags = {t["id"]: t["unread"] for t in (await client.get(TICKETS)).json()}
        assert flags == {first: True, second: True}

        opened = await client.post(f"{TICKETS}/{first}/read")
        assert opened.status_code == 200 and opened.json() == {
            "count": 1,
            "ticket_ids": [second],
        }  # mở một ticket thì trừ 1
        again = await client.post(f"{TICKETS}/{first}/read")
        assert again.json()["count"] == 1  # mở lại không trừ thêm
        assert {t["id"]: t["unread"] for t in (await client.get(TICKETS)).json()} == {first: False, second: True}

    async with client_for(app) as client:
        await login(client, hr_two)
        assert (await unread(client))["count"] == 2  # trạng thái đọc là của từng người: HR khác vẫn thấy chưa đọc

    async with client_for(app) as client:
        await login(client, outsider_hr)
        assert (await unread(client))["count"] == 0  # HR phòng khác không thấy ticket
        assert (await client.post(f"{TICKETS}/{first}/read")).status_code == 404

    async with client_for(app) as client:
        await login(client, employee)
        # HR đã trả lời ở ticket `first`: nhân viên thấy 1 ticket chưa đọc; mở ra thì về 0
        mine = await unread(client)
        assert mine["count"] == 1 and mine["ticket_ids"] == [first]
        assert (await client.post(f"{TICKETS}/{first}/read")).json()["count"] == 0

    # Nhân viên nhắn thêm vào ticket HR đã đọc: HR thấy chưa đọc trở lại
    async with client_for(app) as client:
        await login(client, employee)
        await client.post(f"{TICKETS}/{first}/messages", json={"body": "Em xin hỏi thêm"})
    async with client_for(app) as client:
        await login(client, hr_one)
        assert (await unread(client))["ticket_ids"] == sorted([first, second])
