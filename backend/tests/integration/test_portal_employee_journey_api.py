"""Nhân viên xem lộ trình + tự hoàn thành task, trên PostgreSQL thật (plan-portal/P2/P2.md).

Dựng sẵn 1 JourneyTemplate PUBLISHED + task có phụ thuộc trực tiếp bằng ORM (chưa có API publish/tạo
task thủ công) — chỉ test 2 route thật qua HTTP: `GET /me/journey`, `POST /me/tasks/{id}/complete`.
"""

from collections.abc import AsyncIterator, Awaitable, Callable
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import Settings, get_settings
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.enums import JourneyTemplateStatus, StageVersionStatus
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.stage_version import StageVersion
from src.model.task_dependency import TaskDependency
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"

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
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-emp-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name="Người thử", role=role, password_hash=hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(TeamMember(team_id=team_id, user_id=user.id))
            await session.commit()
            created.append(email)
            return SimpleNamespace(email=email, password=PASSWORD, id=user.id, role=role)

    yield make
    async with session_factory() as session:
        user_ids = (await session.scalars(select(User.id).where(User.email.in_(created)))).all()
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(user_ids)))
        await session.execute(delete(User).where(User.email.in_(created)))
        await session.commit()


@pytest.fixture
async def published_template(
    session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace
) -> AsyncIterator[SimpleNamespace]:
    """1 template PUBLISHED, 1 stage, 2 task — task 2 phụ thuộc task 1 (chỉ AND, P0A D8)."""
    async with session_factory() as session:
        creator_email = f"portal-creator-{uuid4().hex[:10]}@example.test"
        creator = User(email=creator_email, display_name="HR thử", role="HR", password_hash=hash_password(PASSWORD))
        session.add(creator)
        await session.flush()
        tpl = JourneyTemplate(
            code=f"tpl-{uuid4().hex[:8]}",
            title="Lộ trình thử",
            status=JourneyTemplateStatus.PUBLISHED.value,
            team_id=team.id,
            created_by=creator.id,
        )
        session.add(tpl)
        await session.flush()
        stage = JourneyStage(journey_template_id=tpl.id, title="Ngày 1", sort_order=1)
        session.add(stage)
        await session.flush()
        version = StageVersion(journey_stage_id=stage.id, version_no=1, status=StageVersionStatus.APPLIED.value)
        session.add(version)
        await session.flush()
        task1 = TaskTemplate(
            journey_stage_id=stage.id,
            stage_version_id=version.id,
            title="Nhận laptop",
            body_markdown="Nhận laptop tầng 12.",
        )
        task2 = TaskTemplate(
            journey_stage_id=stage.id,
            stage_version_id=version.id,
            title="Đăng nhập Outlook",
            body_markdown="Đăng nhập Outlook.",
        )
        session.add_all([task1, task2])
        await session.flush()
        session.add(TaskDependency(task_template_id=task2.id, depends_on_task_template_id=task1.id))
        await session.commit()
        result = SimpleNamespace(id=tpl.id, task1_id=task1.id, task2_id=task2.id, creator_email=creator_email)
    yield result
    async with session_factory() as session:
        journey_ids = list(
            (
                await session.scalars(
                    select(EmployeeJourney.id).where(EmployeeJourney.journey_template_id == result.id)
                )
            ).all()
        )
        if journey_ids:
            await session.execute(delete(EmployeeTask).where(EmployeeTask.employee_journey_id.in_(journey_ids)))
            await session.execute(delete(EmployeeJourney).where(EmployeeJourney.id.in_(journey_ids)))
        await session.execute(
            delete(TaskDependency).where(TaskDependency.task_template_id.in_([result.task1_id, result.task2_id]))
        )
        await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_([result.task1_id, result.task2_id])))
        await session.execute(delete(JourneyStage).where(JourneyStage.journey_template_id == result.id))
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.id == result.id))
        await session.execute(delete(User).where(User.email == result.creator_email))
        await session.commit()


async def start_journey(client: httpx.AsyncClient) -> httpx.Response:
    """Nhân viên bấm "Tạo lộ trình" (không còn tự tạo khi mở trang), rồi đọc lại lộ trình."""
    created = await client.post("/api/v1/portal/me/journey")
    assert created.status_code in (200, 201), created.text
    return await client.get("/api/v1/portal/me/journey")


def app_for(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(3, 900)
    application.dependency_overrides[get_settings] = lambda: settings
    return application


def client_for(app: FastAPI) -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=("10.0.0.1", 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


async def login(client: httpx.AsyncClient, user: SimpleNamespace) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})


async def test_first_view_creates_journey_with_locked_and_ready_tasks(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as client:
        await login(client, employee)
        response = await start_journey(client)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["journey_template_id"] == published_template.id
    statuses = {t["task_template_id"]: t["status"] for t in body["tasks"]}
    assert statuses[published_template.task1_id] == "READY"
    assert statuses[published_template.task2_id] == "LOCKED"


async def test_complete_task_unlocks_dependent_and_is_idempotent(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as client:
        await login(client, employee)
        journey_response = await start_journey(client)
        tasks = journey_response.json()["tasks"]
        task1_employee_id = next(t["id"] for t in tasks if t["task_template_id"] == published_template.task1_id)
        task2_employee_id = next(t["id"] for t in tasks if t["task_template_id"] == published_template.task2_id)

        first = await client.post(f"/api/v1/portal/me/tasks/{task1_employee_id}/complete")
        assert first.status_code == 200, first.text
        assert first.json()["status"] == "DONE"

        again = await client.post(f"/api/v1/portal/me/tasks/{task1_employee_id}/complete")
        assert again.status_code == 200
        assert again.json()["status"] == "DONE"  # idempotent

        after = await start_journey(client)
        statuses = {t["id"]: t["status"] for t in after.json()["tasks"]}
        assert statuses[task2_employee_id] == "READY"  # đã mở khóa


async def test_complete_locked_task_is_rejected(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as client:
        await login(client, employee)
        journey_response = await start_journey(client)
        task2_employee_id = next(
            t["id"] for t in journey_response.json()["tasks"] if t["task_template_id"] == published_template.task2_id
        )
        response = await client.post(f"/api/v1/portal/me/tasks/{task2_employee_id}/complete")

    assert response.status_code == 409
    assert response.json()["code"] == "TASK_LOCKED"


async def test_no_team_assigned_is_rejected(
    session_factory: async_sessionmaker[AsyncSession],
    make_member: MakeMember,
) -> None:
    # User không thuộc team nào -> tạo bằng thao tác trực tiếp, không qua fixture `team`.
    async with session_factory() as session:
        email = f"portal-noteam-{uuid4().hex[:10]}@example.test"
        user = User(email=email, display_name="Không có team", role="USER", password_hash=hash_password(PASSWORD))
        session.add(user)
        await session.commit()

    app = app_for(session_factory)
    async with client_for(app) as client:
        await login(client, SimpleNamespace(email=email, password=PASSWORD))
        before = await client.get("/api/v1/portal/me/journey")
        response = await client.post("/api/v1/portal/me/journey")

    assert before.status_code == 404 and before.json()["code"] == "NO_JOURNEY"  # không tự tạo khi mở trang
    assert response.status_code == 409
    assert response.json()["code"] == "NO_TEAM_ASSIGNED"

    async with session_factory() as session:
        await session.execute(delete(User).where(User.email == email))
        await session.commit()


async def test_journey_exposes_group_stage_and_prerequisites(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as client:
        await login(client, employee)
        tasks = (await start_journey(client)).json()["tasks"]
        second = next(t for t in tasks if t["task_template_id"] == published_template.task2_id)
        first = next(t for t in tasks if t["task_template_id"] == published_template.task1_id)
        assert second["prerequisites"] == [{"title": "Nhận laptop", "done": False}]
        assert first["prerequisites"] == []
        assert second["stage_title"] == "Ngày 1"
        assert "task_group" in second

        done = await client.post(f"/api/v1/portal/me/tasks/{first['id']}/complete")
        assert done.status_code == 200
        refreshed = (await start_journey(client)).json()["tasks"]
        second_after = next(t for t in refreshed if t["id"] == second["id"])
        assert second_after["prerequisites"] == [{"title": "Nhận laptop", "done": True}]


async def test_profile_progress_update_name_and_change_password(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
    published_template: SimpleNamespace,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as client:
        await login(client, employee)
        before = (await client.get("/api/v1/portal/me/profile")).json()
        assert before["email"] == employee.email
        assert before["department"] == "Team thử"
        assert before["tasks_total"] == 0 and before["journey_started_at"] is None  # chưa mở lộ trình thì chưa tạo

        await start_journey(client)
        after = (await client.get("/api/v1/portal/me/profile")).json()
        assert after["tasks_total"] == 2 and after["tasks_done"] == 0

        renamed = await client.patch("/api/v1/portal/me/profile", json={"display_name": "  Nguyễn   Văn A "})
        assert renamed.status_code == 200
        assert renamed.json()["display_name"] == "Nguyễn Văn A"
        blank = await client.patch("/api/v1/portal/me/profile", json={"display_name": "   "})
        assert blank.status_code == 422

        wrong = await client.post(
            "/api/v1/portal/me/password", json={"current_password": "sai-mat-khau", "new_password": "MatKhauMoi!456"}
        )
        assert wrong.status_code == 400 and wrong.json()["code"] == "CURRENT_PASSWORD_WRONG"
        short = await client.post(
            "/api/v1/portal/me/password", json={"current_password": PASSWORD, "new_password": "ngan"}
        )
        assert short.status_code == 422
        changed = await client.post(
            "/api/v1/portal/me/password", json={"current_password": PASSWORD, "new_password": "MatKhauMoi!456"}
        )
        assert changed.status_code == 204
        # thiết bị đổi mật khẩu vẫn đăng nhập (nhận cookie mới)
        assert (await client.get("/api/v1/portal/me/profile")).status_code == 200

    async with client_for(app) as other:
        old = await other.post("/api/v1/auth/login", json={"email": employee.email, "password": PASSWORD})
        assert old.status_code == 401
        new = await other.post("/api/v1/auth/login", json={"email": employee.email, "password": "MatKhauMoi!456"})
        assert new.status_code == 200


async def test_employee_document_list_needs_login(
    session_factory: async_sessionmaker[AsyncSession],
    team: SimpleNamespace,
    make_member: MakeMember,
) -> None:
    employee = await make_member("USER", team.id)
    app = app_for(session_factory)

    async with client_for(app) as anonymous:
        assert (await anonymous.get("/api/v1/portal/me/documents")).status_code == 401
    async with client_for(app) as client:
        await login(client, employee)
        response = await client.get("/api/v1/portal/me/documents")
        assert response.status_code == 200
        for item in response.json():
            assert item["latest_version_id"] > 0 and item["title"]
