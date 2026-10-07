"""Phiên bản theo từng ngày và lộ trình RIÊNG của nhân viên (bản sao), trên PostgreSQL thật.

Kế hoạch: plan-portal/logic-task/ke-hoach-phien-ban-ngay-va-lo-trinh-rieng-nhan-vien.md.
Test chính: HR sửa và áp dụng bản mới thì lộ trình đã tạo của nhân viên KHÔNG đổi; nhân viên nhận thông báo "trước và sau"
và tự bấm "Cập nhật" (việc đã làm vẫn là đã xong).
"""

import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings, get_settings
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.audit_log import AuditLog
from src.model.employee_journey import EmployeeJourney
from src.model.employee_stage import EmployeeStage
from src.model.journey_template import JourneyTemplate
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"
API = "/api/v1/portal"

MakeMember = Callable[[str, int], Awaitable[SimpleNamespace]]


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def team(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SimpleNamespace]:
    async with session_factory() as session:
        row = Team(code=f"team-{uuid4().hex[:8]}", name="Team thử")
        session.add(row)
        await session.commit()
        result = SimpleNamespace(id=row.id)
    yield result
    async with session_factory() as session:
        # Lộ trình nhân viên trước (RESTRICT tới phiên bản), rồi tới lộ trình mẫu của team.
        await session.execute(delete(EmployeeJourney).where(EmployeeJourney.team_id == result.id))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.team_id == result.id))
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-ver-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name=f"{role} thử", role=role, password_hash=hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(TeamMember(team_id=team_id, user_id=user.id))
            await session.commit()
            created.append(email)
            return SimpleNamespace(email=email, password=PASSWORD, id=user.id, role=role)

    yield make
    async with session_factory() as session:
        user_ids = (await session.scalars(select(User.id).where(User.email.in_(created)))).all()
        await session.execute(delete(EmployeeJourney).where(EmployeeJourney.user_id.in_(user_ids)))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.created_by.in_(user_ids)))
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(user_ids)))
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        await session.execute(delete(User).where(User.email.in_(created)))
        await session.commit()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=50, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(50, 900)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


async def client_as(app: FastAPI, user: SimpleNamespace) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("10.0.0.1", 5000))
    client = httpx.AsyncClient(transport=transport, base_url="http://test")
    response = await client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})
    assert response.status_code == 200, response.text
    return client


async def add_task(
    hr: httpx.AsyncClient, version_id: int, title: str, body: str, depends_on: list[int] | None = None
) -> dict[str, Any]:
    response = await hr.post(
        f"{API}/stage-versions/{version_id}/tasks",
        json={"title": title, "body_markdown": body, "depends_on": depends_on or []},
    )
    assert response.status_code == 200, response.text
    body_json: dict[str, Any] = response.json()
    return body_json


async def tree_day(hr: httpx.AsyncClient, template_id: int) -> dict[str, Any]:
    tree = (await hr.get(f"{API}/journey-templates/mine")).json()
    return next(stage for t in tree if t["id"] == template_id for stage in t["stages"])


def version_by_no(day: dict[str, Any], number: int) -> dict[str, Any]:
    return next(v for v in day["versions"] if v["version_no"] == number)


def task_by_title(tasks: list[dict[str, Any]], title: str) -> dict[str, Any]:
    return next(t for t in tasks if t["title"] == title)


async def build_roadmap(hr: httpx.AsyncClient) -> SimpleNamespace:
    """Ngày 1 đã áp dụng v1: A (Nhận laptop) <- B (Đăng nhập Outlook) <- C (Ảnh đại diện)."""
    template = (
        await hr.post(f"{API}/journey-templates", json={"code": f"t-{uuid4().hex[:8]}", "title": "Lộ trình thử"})
    ).json()
    stage = (
        await hr.post(f"{API}/journey-templates/{template['id']}/stages", json={"title": "Ngày 1", "sort_order": 1})
    ).json()
    day = await tree_day(hr, template["id"])
    v1 = day["versions"][0]
    a = await add_task(hr, v1["id"], "Nhận laptop", "Nhận laptop tại tầng 12.")
    b = await add_task(hr, v1["id"], "Đăng nhập Outlook", "Đăng nhập Outlook.", [a["id"]])
    c = await add_task(hr, v1["id"], "Ảnh đại diện", "Đặt ảnh đại diện.", [b["id"]])
    applied = await hr.post(f"{API}/stage-versions/{v1['id']}/apply")
    assert applied.status_code == 200, applied.text
    return SimpleNamespace(
        template_id=template["id"], stage_id=stage["id"], v1=v1["id"], a=a["id"], b=b["id"], c=c["id"]
    )


async def new_draft(hr: httpx.AsyncClient, stage_id: int, note: str | None = None) -> dict[str, Any]:
    response = await hr.post(f"{API}/stages/{stage_id}/versions", json={"note": note})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


async def my_tasks(client: httpx.AsyncClient) -> dict[str, dict[str, Any]]:
    response = await client.get(f"{API}/me/journey")
    assert response.status_code == 200, response.text
    return {t["title"]: t for t in response.json()["tasks"]}


# ───────────────────────────── Phiên bản (HR) ─────────────────────────────


async def test_draft_clone_keeps_origin_keys_and_only_drafts_are_editable(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)

    v2 = await new_draft(hr, ids.stage_id, "Bản thử")
    assert v2["version_no"] == 2 and v2["status"] == "DRAFT" and v2["task_count"] == 3
    assert v2["based_on_version_id"] == ids.v1

    day = await tree_day(hr, ids.template_id)
    v1_tasks, v2_tasks = version_by_no(day, 1)["tasks"], version_by_no(day, 2)["tasks"]
    assert [t["title"] for t in v2_tasks] == [t["title"] for t in v1_tasks]
    assert {t["id"] for t in v2_tasks}.isdisjoint({t["id"] for t in v1_tasks})
    # Tiên quyết được ánh xạ sang các việc của bản mới (không trỏ về bản cũ).
    v2_b = task_by_title(v2_tasks, "Đăng nhập Outlook")
    assert v2_b["depends_on"] == [task_by_title(v2_tasks, "Nhận laptop")["id"]]

    async with session_factory() as session:
        keys_v1 = set(
            (
                await session.scalars(select(TaskTemplate.origin_key).where(TaskTemplate.stage_version_id == ids.v1))
            ).all()
        )
        keys_v2 = set(
            (
                await session.scalars(select(TaskTemplate.origin_key).where(TaskTemplate.stage_version_id == v2["id"]))
            ).all()
        )
    assert keys_v1 == keys_v2 and len(keys_v1) == 3  # origin_key giữ nguyên qua các phiên bản

    # Sửa trong bản nháp được; sửa trong bản đang áp dụng bị chặn.
    ok = await hr.patch(
        f"{API}/task-templates/{v2_b['id']}", json={"title": "Đăng nhập Outlook và Teams", "body_markdown": "mới"}
    )
    assert ok.status_code == 200, ok.text
    blocked = await hr.patch(
        f"{API}/task-templates/{task_by_title(v1_tasks, 'Đăng nhập Outlook')['id']}",
        json={"title": "đổi", "body_markdown": "đổi"},
    )
    assert blocked.status_code == 409 and blocked.json()["code"] == "VERSION_NOT_EDITABLE"

    # Tiên quyết chỉ trong CÙNG một phiên bản.
    cross = await hr.patch(
        f"{API}/task-templates/{v2_b['id']}",
        json={"title": "x", "body_markdown": "y", "depends_on": [ids.a]},  # ids.a thuộc v1
    )
    assert cross.status_code == 422 and cross.json()["code"] == "DEPENDENCY_OUT_OF_TEMPLATE"


async def test_apply_archives_previous_keeps_one_applied_and_rejects_bad_states(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    v2 = await new_draft(hr, ids.stage_id)

    applied = await hr.post(f"{API}/stage-versions/{v2['id']}/apply")
    assert applied.status_code == 200 and applied.json()["version"]["status"] == "APPLIED"
    day = await tree_day(hr, ids.template_id)
    assert {v["version_no"]: v["status"] for v in day["versions"]} == {1: "ARCHIVED", 2: "APPLIED"}
    assert day["default_version_id"] == v2["id"]

    again = await hr.post(f"{API}/stage-versions/{v2['id']}/apply")
    assert again.status_code == 409 and again.json()["code"] == "VERSION_NOT_DRAFT"

    # Bản đã áp dụng hoặc lưu trữ không xóa được; bản nháp xóa được; ngày phải còn ít nhất một bản.
    for version_id in (ids.v1, v2["id"]):
        denied = await hr.delete(f"{API}/stage-versions/{version_id}")
        assert denied.status_code == 409 and denied.json()["code"] == "VERSION_NOT_EDITABLE"
    v3 = await new_draft(hr, ids.stage_id)
    assert (await hr.delete(f"{API}/stage-versions/{v3['id']}")).status_code == 204

    # Ngày mới tạo có v1 rỗng: áp dụng bị từ chối.
    empty_stage = (
        await hr.post(f"{API}/journey-templates/{ids.template_id}/stages", json={"title": "Ngày 2", "sort_order": 2})
    ).json()
    empty_day = next(s for s in (await tree_day_all(hr, ids.template_id)) if s["id"] == empty_stage["id"])
    refused = await hr.post(f"{API}/stage-versions/{empty_day['versions'][0]['id']}/apply")
    assert refused.status_code == 409 and refused.json()["code"] == "VERSION_EMPTY"


async def tree_day_all(hr: httpx.AsyncClient, template_id: int) -> list[dict[str, Any]]:
    tree = (await hr.get(f"{API}/journey-templates/mine")).json()
    return [stage for t in tree if t["id"] == template_id for stage in t["stages"]]


async def test_hr_scope_and_roles_are_enforced(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    v2 = await new_draft(hr, ids.stage_id)

    async with session_factory() as session:
        other = Team(code=f"team-{uuid4().hex[:8]}", name="Team khác")
        session.add(other)
        await session.commit()
        other_id = other.id
    try:
        outsider = await client_as(app, await make_member("HR", other_id))
        employee = await client_as(app, await make_member("USER", team.id))
        for client in (outsider, employee):
            for method, url in (
                ("POST", f"{API}/stage-versions/{v2['id']}/apply"),
                ("GET", f"{API}/stage-versions/{v2['id']}/apply-preview"),
                ("GET", f"{API}/stage-versions/{v2['id']}/rollout"),
                ("DELETE", f"{API}/stage-versions/{v2['id']}"),
            ):
                response = await client.request(method, url)
                assert response.status_code == 403, (method, url, response.text)
    finally:
        async with session_factory() as session:
            await session.execute(delete(TeamMember).where(TeamMember.team_id == other_id))
            await session.commit()
        async with session_factory() as session:
            await session.execute(delete(Team).where(Team.id == other_id))
            await session.commit()


# ───────────────────────────── Lộ trình riêng của nhân viên ─────────────────────────────


async def test_journey_is_created_by_the_employee_not_automatically_and_is_idempotent(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    employee = await client_as(app, await make_member("USER", team.id))

    # Chưa có bản nào áp dụng: không có gì để sao chép.
    assert (await employee.get(f"{API}/me/journey")).json()["code"] == "NO_JOURNEY"
    no_template = await employee.post(f"{API}/me/journey")
    assert no_template.status_code == 404 and no_template.json()["code"] == "NO_JOURNEY_TEMPLATE"

    await build_roadmap(hr)
    assert (await employee.get(f"{API}/me/journey")).status_code == 404  # áp dụng xong vẫn không tự tạo
    first = await employee.post(f"{API}/me/journey")
    second = await employee.post(f"{API}/me/journey")
    assert first.status_code == 201 and second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    tasks = await my_tasks(employee)
    assert [t["status"] for t in sorted(tasks.values(), key=lambda t: t["sort_order"])] == ["READY", "LOCKED", "LOCKED"]
    assert tasks["Đăng nhập Outlook"]["prerequisites"] == [{"title": "Nhận laptop", "done": False}]
    assert all(t["pending_change_id"] is None for t in tasks.values())


async def test_hr_adds_a_journey_for_an_employee_of_their_team_only(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    await build_roadmap(hr)
    member = await make_member("USER", team.id)
    employee = await client_as(app, member)
    assert (await employee.get(f"{API}/me/journey")).json()["code"] == "NO_JOURNEY"

    first = await hr.post(f"{API}/employees/{member.id}/journey")
    again = await hr.post(f"{API}/employees/{member.id}/journey")
    assert first.status_code == 201 and first.json()["created"] is True
    assert again.status_code == 200 and again.json() == {"journey_id": first.json()["journey_id"], "created": False}
    assert len(await my_tasks(employee)) == 3  # nhân viên thấy lộ trình HR vừa thêm

    # Người không phải nhân viên, người không tồn tại, nhân viên (không phải HR) và HR khác team đều bị chặn.
    other_hr_member = await make_member("HR", team.id)
    assert (await hr.post(f"{API}/employees/{other_hr_member.id}/journey")).status_code == 404
    assert (await hr.post(f"{API}/employees/999999999/journey")).status_code == 404
    assert (await employee.post(f"{API}/employees/{member.id}/journey")).status_code == 403
    async with session_factory() as session:
        other = Team(code=f"team-{uuid4().hex[:8]}", name="Team khác")
        session.add(other)
        await session.commit()
        other_id = other.id
    try:
        outsider_hr = await client_as(app, await make_member("HR", other_id))
        target = await make_member("USER", team.id)
        assert (await outsider_hr.post(f"{API}/employees/{target.id}/journey")).status_code == 403
        assert (await employee.get(f"{API}/me/journey")).status_code == 200
    finally:
        async with session_factory() as session:
            await session.execute(delete(TeamMember).where(TeamMember.team_id == other_id))
            await session.commit()
        async with session_factory() as session:
            await session.execute(delete(Team).where(Team.id == other_id))
            await session.commit()


# ───────────────────────────── Áp dụng bản mới: báo và để nhân viên tự cập nhật ─────────────────────────────


async def test_applying_adds_and_removes_automatically_and_employees_only_confirm_edited_tasks(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    an = await client_as(app, await make_member("USER", team.id))
    binh = await client_as(app, await make_member("USER", team.id))
    for client in (an, binh):
        assert (await client.post(f"{API}/me/journey")).status_code == 201
    an_tasks = await my_tasks(an)
    done = await an.post(f"{API}/me/tasks/{an_tasks['Nhận laptop']['id']}/complete")
    assert done.status_code == 200
    original_body = an_tasks["Nhận laptop"]["body_markdown"]

    # HR soạn v2: sửa A, sửa B, bỏ C, thêm D (cần B).
    v2 = await new_draft(hr, ids.stage_id)
    day = await tree_day(hr, ids.template_id)
    v2_tasks = version_by_no(day, 2)["tasks"]
    a2, b2, c2 = (task_by_title(v2_tasks, t) for t in ("Nhận laptop", "Đăng nhập Outlook", "Ảnh đại diện"))
    assert (
        await hr.patch(
            f"{API}/task-templates/{a2['id']}",
            json={"title": "Nhận laptop", "body_markdown": "Nhận laptop tại tầng 14.", "depends_on": []},
        )
    ).status_code == 200
    assert (
        await hr.patch(
            f"{API}/task-templates/{b2['id']}",
            json={
                "title": "Đăng nhập Outlook và Teams",
                "body_markdown": "Đăng nhập Outlook.",
                "depends_on": [a2["id"]],
            },
        )
    ).status_code == 200
    assert (await hr.delete(f"{API}/task-templates/{c2['id']}")).status_code == 204
    await add_task(hr, v2["id"], "Ký hợp đồng", "Ký hợp đồng cuối ngày.", [b2["id"]])

    preview = await hr.get(f"{API}/stage-versions/{v2['id']}/apply-preview")
    assert preview.json() == {"modified": 2, "added": 1, "removed": 1, "employee_count": 2, "has_applied_before": True}

    applied = await hr.post(f"{API}/stage-versions/{v2['id']}/apply")
    assert applied.status_code == 200 and applied.json()["notified_count"] == 2

    # (1) Thêm và bỏ việc được áp dụng NGAY (nhân viên không phải bấm gì); việc bị SỬA vẫn giữ nội dung cũ chờ nhân viên xem.
    for client in (an, binh):
        tasks = await my_tasks(client)
        assert set(tasks) == {"Nhận laptop", "Đăng nhập Outlook", "Ký hợp đồng"}  # D đã thêm, C đã rời lộ trình
        assert tasks["Nhận laptop"]["body_markdown"] == original_body
        assert tasks["Ký hợp đồng"]["status"] == "LOCKED"  # cần B, B chưa xong
    after_apply = await my_tasks(an)
    assert after_apply["Nhận laptop"]["status"] == "DONE" and after_apply["Đăng nhập Outlook"]["status"] == "READY"
    assert after_apply["Nhận laptop"]["pending_change_id"] is not None  # nhãn "Có chỉnh sửa"
    assert after_apply["Ký hợp đồng"]["pending_change_id"] is None  # việc mới không cần chấp nhận

    # (2) Thông báo có TRƯỚC và SAU, kèm việc đã làm hay chưa.
    notices = (await an.get(f"{API}/me/journey/notices")).json()
    assert len(notices) == 1 and notices[0]["stage_title"] == "Ngày 1" and notices[0]["version_no"] == 2
    changes = {c["task_title"]: c for c in notices[0]["changes"]}
    assert {title: c["kind"] for title, c in changes.items()} == {
        "Nhận laptop": "MODIFIED",
        "Đăng nhập Outlook và Teams": "MODIFIED",
        "Ảnh đại diện": "REMOVED",
        "Ký hợp đồng": "ADDED",
    }
    laptop = changes["Nhận laptop"]
    assert laptop["status"] == "PENDING" and laptop["employee_status"] == "DONE"
    assert (
        changes["Ảnh đại diện"]["status"] == "ACCEPTED" and changes["Ký hợp đồng"]["status"] == "ACCEPTED"
    )  # tự áp dụng
    assert notices[0]["new_stage"] is False
    assert laptop["before"]["body_markdown"] == "Nhận laptop tại tầng 12."
    assert laptop["after"]["body_markdown"] == "Nhận laptop tại tầng 14."
    assert laptop["changed_fields"] == ["body_markdown"]
    assert changes["Đăng nhập Outlook và Teams"]["employee_status"] == "READY"
    assert changes["Đăng nhập Outlook và Teams"]["changed_fields"] == ["title"]

    # (3) Ghi chú trước khi bấm "Cập nhật" cho việc đã làm: vẫn là đã xong.
    note_done = (await an.get(f"{API}/me/journey/changes/{laptop['id']}/preview")).json()
    assert note_done["keeps_done"] is True and note_done["also_update"] == [] and note_done["locked_until"] == []
    already = await an.get(f"{API}/me/journey/changes/{changes['Ký hợp đồng']['id']}/preview")
    assert already.status_code == 409  # việc thêm đã được áp dụng, không còn gì để xem trước

    # (4) An bấm "Cập nhật" hai việc bị sửa.
    for title in ("Nhận laptop", "Đăng nhập Outlook và Teams"):
        response = await an.post(f"{API}/me/journey/changes/{changes[title]['id']}/accept")
        assert response.status_code == 200, (title, response.text)
    updated = await my_tasks(an)
    assert set(updated) == {"Nhận laptop", "Đăng nhập Outlook và Teams", "Ký hợp đồng"}  # việc bị bỏ đã rời lộ trình
    assert updated["Nhận laptop"]["body_markdown"] == "Nhận laptop tại tầng 14."
    assert updated["Nhận laptop"]["status"] == "DONE"  # việc đã làm vẫn là đã xong
    assert updated["Đăng nhập Outlook và Teams"]["status"] == "READY"  # việc chưa làm giữ nguyên trạng thái
    assert updated["Ký hợp đồng"]["status"] == "LOCKED"
    assert updated["Ký hợp đồng"]["prerequisites"] == [{"title": "Đăng nhập Outlook và Teams", "done": False}]
    assert all(t["pending_change_id"] is None for t in updated.values())
    async with session_factory() as session:
        sources = (
            await session.scalars(
                select(EmployeeStage.source_stage_version_id)
                .join(EmployeeJourney, EmployeeJourney.id == EmployeeStage.employee_journey_id)
                .where(EmployeeJourney.user_id.in_(select(User.id).where(User.email.like("portal-ver-%"))))
            )
        ).all()
    assert v2["id"] in sources  # ngày của An đã theo kịp bản mới

    # (5) Bình bấm "Giữ bản cũ" cho hai việc bị sửa: nội dung giữ nguyên (việc thêm/bỏ đã tự áp dụng từ trước).
    binh_notice = (await binh.get(f"{API}/me/journey/notices")).json()[0]
    for change in (c for c in binh_notice["changes"] if c["status"] == "PENDING"):
        assert (await binh.post(f"{API}/me/journey/changes/{change['id']}/dismiss")).status_code == 204
    kept = await my_tasks(binh)
    assert set(kept) == {"Nhận laptop", "Đăng nhập Outlook", "Ký hợp đồng"}
    assert kept["Nhận laptop"]["body_markdown"] == original_body

    # (6) HR theo dõi triển khai.
    rollout = (await hr.get(f"{API}/stage-versions/{v2['id']}/rollout")).json()
    assert sorted(row["state"] for row in rollout) == ["KEPT_OLD", "UPDATED"]

    # (7) Nhân viên tạo lộ trình SAU khi áp dụng nhận ngay bản mới, không có thông báo.
    chi = await client_as(app, await make_member("USER", team.id))
    assert (await chi.post(f"{API}/me/journey")).status_code == 201
    fresh = await my_tasks(chi)
    assert set(fresh) == {"Nhận laptop", "Đăng nhập Outlook và Teams", "Ký hợp đồng"}
    assert fresh["Nhận laptop"]["body_markdown"] == "Nhận laptop tại tầng 14."
    assert (await chi.get(f"{API}/me/journey/notices")).json() == []


async def test_not_done_task_keeps_its_content_until_the_employee_presses_update_and_may_relock(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    employee = await client_as(app, await make_member("USER", team.id))
    assert (await employee.post(f"{API}/me/journey")).status_code == 201
    laptop_id = (await my_tasks(employee))["Nhận laptop"]["id"]
    assert (await employee.post(f"{API}/me/tasks/{laptop_id}/complete")).status_code == 200

    # v2: Ảnh đại diện (C) cần thêm tiên quyết là việc MỚI "Chụp ảnh" (E) => khi cập nhật C phải cập nhật kèm E.
    v2 = await new_draft(hr, ids.stage_id)
    day = await tree_day(hr, ids.template_id)
    v2_tasks = version_by_no(day, 2)["tasks"]
    b2, c2 = task_by_title(v2_tasks, "Đăng nhập Outlook"), task_by_title(v2_tasks, "Ảnh đại diện")
    e = await add_task(hr, v2["id"], "Chụp ảnh", "Chụp ảnh chân dung.")
    assert (
        await hr.patch(
            f"{API}/task-templates/{c2['id']}",
            json={"title": "Ảnh đại diện", "body_markdown": "Đặt ảnh đại diện.", "depends_on": [b2["id"], e["id"]]},
        )
    ).status_code == 200
    assert (await hr.post(f"{API}/stage-versions/{v2['id']}/apply")).status_code == 200

    notice = (await employee.get(f"{API}/me/journey/notices")).json()[0]
    changes = {c["task_title"]: c for c in notice["changes"]}
    assert set(changes) == {"Ảnh đại diện", "Chụp ảnh"}
    assert changes["Chụp ảnh"]["status"] == "ACCEPTED"  # việc mới đã tự vào lộ trình
    assert (await my_tasks(employee))["Chụp ảnh"]["status"] == "READY"
    note = (await employee.get(f"{API}/me/journey/changes/{changes['Ảnh đại diện']['id']}/preview")).json()
    assert note["also_update"] == []  # việc liên quan đã được thêm sẵn, không cần cập nhật kèm
    assert note["locked_until"] == ["Chụp ảnh", "Đăng nhập Outlook"]  # sắp theo tên để ổn định

    accepted = await employee.post(f"{API}/me/journey/changes/{changes['Ảnh đại diện']['id']}/accept")
    assert accepted.json()["updated_change_ids"] == [changes["Ảnh đại diện"]["id"]]
    after = await my_tasks(employee)
    assert after["Chụp ảnh"]["status"] == "READY"  # việc mới không có tiên quyết
    assert after["Ảnh đại diện"]["status"] == "LOCKED"
    assert {p["title"] for p in after["Ảnh đại diện"]["prerequisites"]} == {"Đăng nhập Outlook", "Chụp ảnh"}
    again = await employee.post(f"{API}/me/journey/changes/{changes['Ảnh đại diện']['id']}/accept")
    assert again.status_code == 200  # bấm lại không nhân đôi
    assert sum(1 for t in (await my_tasks(employee)).values() if t["title"] == "Chụp ảnh") == 1


async def test_a_newer_version_supersedes_the_pending_change_and_is_computed_from_the_employees_copy(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    employee = await client_as(app, await make_member("USER", team.id))
    assert (await employee.post(f"{API}/me/journey")).status_code == 201

    async def release(body: str) -> dict[str, Any]:
        draft = await new_draft(hr, ids.stage_id)
        day = await tree_day(hr, ids.template_id)
        task = task_by_title(version_by_no(day, draft["version_no"])["tasks"], "Nhận laptop")
        assert (
            await hr.patch(
                f"{API}/task-templates/{task['id']}",
                json={"title": "Nhận laptop", "body_markdown": body, "depends_on": []},
            )
        ).status_code == 200
        assert (await hr.post(f"{API}/stage-versions/{draft['id']}/apply")).status_code == 200
        return draft

    await release("Nhận laptop tại tầng 14.")
    first_notice = (await employee.get(f"{API}/me/journey/notices")).json()[0]
    old_change = first_notice["changes"][0]["id"]
    await release("Nhận laptop tại tầng 16.")

    notices = (await employee.get(f"{API}/me/journey/notices")).json()
    by_version = {n["version_no"]: n for n in notices}
    assert by_version[2]["changes"][0]["status"] == "SUPERSEDED"
    newest = by_version[3]["changes"][0]
    assert newest["status"] == "PENDING"
    assert (
        newest["before"]["body_markdown"] == "Nhận laptop tại tầng 12."
    )  # trước = nội dung của CHÍNH nhân viên, không phải v2
    assert newest["after"]["body_markdown"] == "Nhận laptop tại tầng 16."

    stale = await employee.post(f"{API}/me/journey/changes/{old_change}/accept")
    assert stale.status_code == 409 and stale.json()["code"] == "CHANGE_SUPERSEDED"
    assert (await employee.post(f"{API}/me/journey/changes/{newest['id']}/accept")).status_code == 200
    assert (await my_tasks(employee))["Nhận laptop"]["body_markdown"] == "Nhận laptop tại tầng 16."


async def test_notices_and_changes_are_private_to_their_owner(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    owner = await client_as(app, await make_member("USER", team.id))
    stranger = await client_as(app, await make_member("USER", team.id))
    assert (await owner.post(f"{API}/me/journey")).status_code == 201
    draft = await new_draft(hr, ids.stage_id)
    day = await tree_day(hr, ids.template_id)
    task = task_by_title(version_by_no(day, draft["version_no"])["tasks"], "Nhận laptop")
    await hr.patch(
        f"{API}/task-templates/{task['id']}", json={"title": "Nhận laptop", "body_markdown": "mới", "depends_on": []}
    )
    await hr.post(f"{API}/stage-versions/{draft['id']}/apply")

    notice = (await owner.get(f"{API}/me/journey/notices")).json()[0]
    change_id = notice["changes"][0]["id"]
    assert (await stranger.get(f"{API}/me/journey/notices")).json() == []
    for method, url in (
        ("GET", f"{API}/me/journey/changes/{change_id}/preview"),
        ("POST", f"{API}/me/journey/changes/{change_id}/accept"),
        ("POST", f"{API}/me/journey/changes/{change_id}/dismiss"),
        ("POST", f"{API}/me/journey/notices/{notice['id']}/read"),
        ("POST", f"{API}/me/journey/notices/{notice['id']}/accept-all"),
    ):
        response = await stranger.request(method, url)
        assert response.status_code == 404, (method, url, response.text)
    assert (await owner.post(f"{API}/me/journey/notices/{notice['id']}/read")).status_code == 204
    read = (await owner.get(f"{API}/me/journey/notices")).json()[0]
    assert read["read_at"] is not None


async def test_removing_a_prerequisite_unlocks_the_dependents_and_a_done_task_is_never_removed(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)  # A <- B <- C
    employee = await client_as(app, await make_member("USER", team.id))
    assert (await employee.post(f"{API}/me/journey")).status_code == 201
    tasks = await my_tasks(employee)
    assert (await employee.post(f"{API}/me/tasks/{tasks['Nhận laptop']['id']}/complete")).status_code == 200

    # v2 bỏ A (đã làm) và B (chưa làm); C chỉ còn lại và hết tiên quyết.
    v2 = await new_draft(hr, ids.stage_id)
    day = await tree_day(hr, ids.template_id)
    v2_tasks = version_by_no(day, 2)["tasks"]
    for title in ("Nhận laptop", "Đăng nhập Outlook"):
        assert (await hr.delete(f"{API}/task-templates/{task_by_title(v2_tasks, title)['id']}")).status_code == 204
    assert (await hr.post(f"{API}/stage-versions/{v2['id']}/apply")).status_code == 200

    notice = (await employee.get(f"{API}/me/journey/notices")).json()[0]
    changes = {c["task_title"]: c for c in notice["changes"]}
    assert changes["Nhận laptop"]["informational"] is True  # việc đã làm bị bỏ: chỉ báo thông tin, không có nút
    assert changes["Nhận laptop"]["status"] == "DISMISSED"
    assert changes["Đăng nhập Outlook"]["kind"] == "REMOVED" and changes["Đăng nhập Outlook"]["informational"] is False
    assert changes["Đăng nhập Outlook"]["status"] == "ACCEPTED"  # việc chưa làm bị bỏ: tự rời lộ trình
    assert changes["Ảnh đại diện"]["kind"] == "PREREQUISITES" and changes["Ảnh đại diện"]["status"] == "PENDING"
    assert set(await my_tasks(employee)) == {"Nhận laptop", "Ảnh đại diện"}
    assert (await my_tasks(employee))["Ảnh đại diện"]["status"] == "READY"  # tiên quyết đã rời lộ trình nên hết khóa

    accepted = await employee.post(f"{API}/me/journey/notices/{notice['id']}/accept-all")
    assert accepted.status_code == 200
    after = await my_tasks(employee)
    assert set(after) == {"Nhận laptop", "Ảnh đại diện"}  # B (chưa làm) rời lộ trình; A (đã làm) ở lại
    assert after["Nhận laptop"]["status"] == "DONE"
    assert after["Ảnh đại diện"]["status"] == "READY" and after["Ảnh đại diện"]["prerequisites"] == []

    rollout = (await hr.get(f"{API}/stage-versions/{v2['id']}/rollout")).json()
    assert [row["state"] for row in rollout] == ["UPDATED"]


async def test_a_day_added_after_journeys_exist_reaches_employees_as_one_notice_without_accepting_each_task(
    app: FastAPI, team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    employee = await client_as(app, await make_member("USER", team.id))
    assert (await employee.post(f"{API}/me/journey")).status_code == 201

    stage2 = (
        await hr.post(f"{API}/journey-templates/{ids.template_id}/stages", json={"title": "Ngày 2", "sort_order": 2})
    ).json()
    day2 = next(d for d in await tree_day_all(hr, ids.template_id) if d["id"] == stage2["id"])
    x = await add_task(hr, day2["versions"][0]["id"], "Đào tạo hội nhập", "Đến phòng đào tạo.")
    await add_task(hr, day2["versions"][0]["id"], "Làm bài kiểm tra", "Làm bài.", [x["id"]])
    applied = await hr.post(f"{API}/stage-versions/{day2['versions'][0]['id']}/apply")
    assert applied.status_code == 200 and applied.json()["notified_count"] == 1

    # Một thông báo "bạn có ngày mới"; các việc của ngày đó vào lộ trình ngay, nhân viên không phải bấm chấp nhận từng việc.
    notices = (await employee.get(f"{API}/me/journey/notices")).json()
    assert len(notices) == 1
    notice = notices[0]
    assert notice["stage_title"] == "Ngày 2" and notice["new_stage"] is True
    assert {c["kind"] for c in notice["changes"]} == {"ADDED"} and {c["status"] for c in notice["changes"]} == {
        "ACCEPTED"
    }
    tasks = await my_tasks(employee)
    assert set(tasks) == {"Nhận laptop", "Đăng nhập Outlook", "Ảnh đại diện", "Đào tạo hội nhập", "Làm bài kiểm tra"}
    assert tasks["Đào tạo hội nhập"]["status"] == "READY" and tasks["Làm bài kiểm tra"]["status"] == "LOCKED"
    assert tasks["Đào tạo hội nhập"]["stage_title"] == "Ngày 2"
    assert tasks["Làm bài kiểm tra"]["prerequisites"] == [{"title": "Đào tạo hội nhập", "done": False}]


async def test_concurrent_applies_and_concurrent_journey_creation_leave_exactly_one_winner(
    app: FastAPI, session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await client_as(app, await make_member("HR", team.id))
    ids = await build_roadmap(hr)
    v2, v3 = await new_draft(hr, ids.stage_id), await new_draft(hr, ids.stage_id)

    results = await asyncio.gather(
        hr.post(f"{API}/stage-versions/{v2['id']}/apply"),
        hr.post(f"{API}/stage-versions/{v3['id']}/apply"),
        return_exceptions=True,
    )

    assert all(
        not isinstance(r, BaseException) and r.status_code == 200 for r in results
    )  # nối tiếp nhau nhờ khóa dòng ngày
    day = await tree_day(hr, ids.template_id)
    assert sorted(v["status"] for v in day["versions"]).count("APPLIED") == 1

    member = await make_member("USER", team.id)
    employee = await client_as(app, member)
    created = await asyncio.gather(employee.post(f"{API}/me/journey"), employee.post(f"{API}/me/journey"))
    assert sorted(r.status_code for r in created) in ([200, 201], [201, 201])
    async with session_factory() as session:
        journeys = (await session.scalars(select(EmployeeJourney.id).where(EmployeeJourney.user_id == member.id))).all()
    assert len(journeys) == 1  # index duy nhất từng phần: yêu cầu thua lấy lại lộ trình của yêu cầu thắng
