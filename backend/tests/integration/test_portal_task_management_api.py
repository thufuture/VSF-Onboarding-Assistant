"""HR quản lý task thủ công trên PostgreSQL thật: thứ tự, tiên quyết (AND, không vòng), xuất bản, sửa tài liệu."""

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
from src.model.audit_log import AuditLog
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
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
        template_ids = list(
            (await session.scalars(select(JourneyTemplate.id).where(JourneyTemplate.team_id == result.id))).all()
        )
        if template_ids:
            stage_ids = list(
                (
                    await session.scalars(
                        select(JourneyStage.id).where(JourneyStage.journey_template_id.in_(template_ids))
                    )
                ).all()
            )
            if stage_ids:
                task_ids = list(
                    (
                        await session.scalars(
                            select(TaskTemplate.id).where(TaskTemplate.journey_stage_id.in_(stage_ids))
                        )
                    ).all()
                )
                if task_ids:
                    await session.execute(delete(TaskDependency).where(TaskDependency.task_template_id.in_(task_ids)))
                    await session.execute(delete(TaskTemplate).where(TaskTemplate.id.in_(task_ids)))
                await session.execute(delete(JourneyStage).where(JourneyStage.id.in_(stage_ids)))
            await session.execute(delete(JourneyTemplate).where(JourneyTemplate.id.in_(template_ids)))
        await session.execute(delete(Team).where(Team.id == result.id))
        await session.commit()


@pytest.fixture
async def make_member(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-mgmt-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name="HR thử", role=role, password_hash=hash_password(PASSWORD))
            session.add(user)
            await session.flush()
            session.add(TeamMember(team_id=team_id, user_id=user.id))
            await session.commit()
            created.append(email)
            return SimpleNamespace(email=email, password=PASSWORD, id=user.id, role=role)

    yield make
    async with session_factory() as session:
        user_ids = (await session.scalars(select(User.id).where(User.email.in_(created)))).all()
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.created_by.in_(user_ids)))
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(user_ids)))
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        await session.execute(delete(User).where(User.email.in_(created)))
        await session.commit()


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


async def _draft_stage(client: httpx.AsyncClient) -> int:
    template = await client.post(
        "/api/v1/portal/journey-templates", json={"code": f"t-{uuid4().hex[:8]}", "title": "Lộ trình thử"}
    )
    assert template.status_code == 200, template.text
    stage = await client.post(
        f"/api/v1/portal/journey-templates/{template.json()['id']}/stages", json={"title": "Ngày 1", "sort_order": 1}
    )
    assert stage.status_code == 200, stage.text
    return int(stage.json()["id"])


async def test_order_dependencies_and_cycle_rejection(
    session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await make_member("HR", team.id)
    async with client_for(app_for(session_factory)) as client:
        await client.post("/api/v1/auth/login", json={"email": hr.email, "password": hr.password})
        stage_id = await _draft_stage(client)

        a = (
            await client.post(f"/api/v1/portal/stages/{stage_id}/tasks", json={"title": "A", "body_markdown": "a"})
        ).json()
        b = (
            await client.post(
                f"/api/v1/portal/stages/{stage_id}/tasks",
                json={"title": "B", "body_markdown": "b", "depends_on": [a["id"]]},
            )
        ).json()
        # chèn C vào đầu (vị trí 1) -> A,B dịch xuống
        c = (
            await client.post(
                f"/api/v1/portal/stages/{stage_id}/tasks", json={"title": "C", "body_markdown": "c", "sort_order": 1}
            )
        ).json()

        tree = (await client.get("/api/v1/portal/journey-templates/mine")).json()
        tasks = next(s for tpl in tree for s in tpl["stages"] if s["id"] == stage_id)["tasks"]
        assert [t["title"] for t in tasks] == ["C", "A", "B"]
        assert [t["sort_order"] for t in tasks] == [1, 2, 3]
        assert next(t for t in tasks if t["id"] == b["id"])["depends_on"] == [a["id"]]

        # A phụ thuộc B trong khi B đã phụ thuộc A -> vòng
        cycle = await client.patch(
            f"/api/v1/portal/task-templates/{a['id']}",
            json={"title": "A", "body_markdown": "a", "depends_on": [b["id"]]},
        )
        assert cycle.status_code == 422
        assert cycle.json()["code"] == "DEPENDENCY_CYCLE"

        # tự trỏ vào mình
        selfdep = await client.patch(
            f"/api/v1/portal/task-templates/{c['id']}",
            json={"title": "C", "body_markdown": "c", "depends_on": [c["id"]]},
        )
        assert selfdep.status_code == 422


async def test_publish_locks_template_and_empty_publish_rejected(
    session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await make_member("HR", team.id)
    async with client_for(app_for(session_factory)) as client:
        await client.post("/api/v1/auth/login", json={"email": hr.email, "password": hr.password})
        template = (
            await client.post(
                "/api/v1/portal/journey-templates", json={"code": f"t-{uuid4().hex[:8]}", "title": "Lộ trình thử"}
            )
        ).json()
        stage = (
            await client.post(
                f"/api/v1/portal/journey-templates/{template['id']}/stages", json={"title": "Ngày 1", "sort_order": 1}
            )
        ).json()

        empty = await client.post(f"/api/v1/portal/journey-templates/{template['id']}/publish")
        assert empty.status_code == 409
        assert empty.json()["code"] == "TEMPLATE_EMPTY"

        await client.post(f"/api/v1/portal/stages/{stage['id']}/tasks", json={"title": "A", "body_markdown": "a"})
        published = await client.post(f"/api/v1/portal/journey-templates/{template['id']}/publish")
        assert published.status_code == 200
        assert published.json()["status"] == "PUBLISHED"

        locked = await client.post(
            f"/api/v1/portal/stages/{stage['id']}/tasks", json={"title": "B", "body_markdown": "b"}
        )
        assert locked.status_code == 409
        assert locked.json()["code"] == "TEMPLATE_ALREADY_PUBLISHED"


async def test_task_group_is_saved_updated_and_validated(
    session_factory: async_sessionmaker[AsyncSession], team: SimpleNamespace, make_member: MakeMember
) -> None:
    hr = await make_member("HR", team.id)
    async with client_for(app_for(session_factory)) as client:
        await client.post("/api/v1/auth/login", json={"email": hr.email, "password": hr.password})
        stage_id = await _draft_stage(client)

        created = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks",
            json={"title": "Nhận laptop", "body_markdown": "x", "task_group": "DEVICE"},
        )
        assert created.status_code == 200, created.text
        assert created.json()["task_group"] == "DEVICE"

        # không gửi nhóm thì task chưa phân nhóm (NULL)
        plain = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks", json={"title": "Việc khác", "body_markdown": "y"}
        )
        assert plain.json()["task_group"] is None

        updated = await client.patch(
            f"/api/v1/portal/task-templates/{created.json()['id']}",
            json={"title": "Nhận laptop", "body_markdown": "x", "task_group": "OFFICE"},
        )
        assert updated.json()["task_group"] == "OFFICE"

        tree = (await client.get("/api/v1/portal/journey-templates/mine")).json()
        tasks = next(s for tpl in tree for s in tpl["stages"] if s["id"] == stage_id)["tasks"]
        assert {t["title"]: t["task_group"] for t in tasks} == {"Nhận laptop": "OFFICE", "Việc khác": None}

        invalid = await client.post(
            f"/api/v1/portal/stages/{stage_id}/tasks",
            json={"title": "Sai nhóm", "body_markdown": "z", "task_group": "NOPE"},
        )
        assert invalid.status_code == 422
