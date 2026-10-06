"""RBAC/scope của Portal trên PostgreSQL thật (plan-portal/P1/P1.md mục 4 — Definition of Done).

Kiểm: role USER bị chặn ở `/portal/journeys` (chỉ HR/ADMIN); HR đúng team qua được; HR khác team bị
chặn bởi `require_team_scope` (403 FORBIDDEN_TEAM_SCOPE); ADMIN luôn qua bất kể team.
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
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"

TwoTeams = tuple[SimpleNamespace, SimpleNamespace]
MakeMember = Callable[[str, int], Awaitable[SimpleNamespace]]


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def two_teams(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[TwoTeams]:
    async with session_factory() as session:
        team_a = Team(code=f"team-a-{uuid4().hex[:8]}", name="Team A")
        team_b = Team(code=f"team-b-{uuid4().hex[:8]}", name="Team B")
        session.add_all([team_a, team_b])
        await session.commit()
        ids = (SimpleNamespace(id=team_a.id), SimpleNamespace(id=team_b.id))
    yield ids
    async with session_factory() as session:
        await session.execute(delete(Team).where(Team.id.in_([t.id for t in ids])))
        await session.commit()


@pytest.fixture
async def make_member(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[MakeMember]:
    created: list[str] = []

    async def make(role: str, team_id: int) -> SimpleNamespace:
        email = f"portal-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name="Người thử Portal", role=role, password_hash=hash_password(PASSWORD))
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
def app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
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


async def test_user_role_forbidden(app: FastAPI, two_teams: TwoTeams, make_member: MakeMember) -> None:
    team_a, _team_b = two_teams
    employee = await make_member("USER", team_a.id)
    async with client_for(app) as client:
        await login(client, employee)
        response = await client.get("/api/v1/portal/journeys", params={"team_id": team_a.id})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_ROLE"


async def test_hr_same_team_allowed(app: FastAPI, two_teams: TwoTeams, make_member: MakeMember) -> None:
    team_a, _team_b = two_teams
    hr = await make_member("HR", team_a.id)
    async with client_for(app) as client:
        await login(client, hr)
        response = await client.get("/api/v1/portal/journeys", params={"team_id": team_a.id})
    assert response.status_code == 200
    assert response.json() == {"team_id": team_a.id, "journeys": []}


async def test_hr_other_team_forbidden(app: FastAPI, two_teams: TwoTeams, make_member: MakeMember) -> None:
    team_a, team_b = two_teams
    hr_of_b = await make_member("HR", team_b.id)
    async with client_for(app) as client:
        await login(client, hr_of_b)
        response = await client.get("/api/v1/portal/journeys", params={"team_id": team_a.id})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_TEAM_SCOPE"


async def test_admin_bypasses_team_scope(app: FastAPI, two_teams: TwoTeams, make_member: MakeMember) -> None:
    team_a, _team_b = two_teams
    admin = await make_member("ADMIN", _team_b.id)  # admin thuộc team khác, vẫn phải qua được
    async with client_for(app) as client:
        await login(client, admin)
        response = await client.get("/api/v1/portal/journeys", params={"team_id": team_a.id})
    assert response.status_code == 200


async def test_portal_me_any_role(app: FastAPI, two_teams: TwoTeams, make_member: MakeMember) -> None:
    team_a, _team_b = two_teams
    employee = await make_member("USER", team_a.id)
    async with client_for(app) as client:
        await login(client, employee)
        response = await client.get("/api/v1/portal/me")
    assert response.status_code == 200
    assert response.json() == {"user_id": employee.id, "role": "USER"}
