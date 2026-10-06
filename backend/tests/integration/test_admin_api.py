"""Quản trị hệ thống trên PostgreSQL thật: chỉ ADMIN, người dùng, phòng ban, thành viên, sao lộ trình mẫu, nhật ký."""

from collections.abc import AsyncIterator
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
from src.model.journey_template import JourneyTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"
TAG = f"adm-{uuid4().hex[:8]}"


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def people(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[SimpleNamespace]:
    async with session_factory() as session:
        admin = User(email=f"{TAG}-admin@example.test", display_name="Admin thử", role="ADMIN")
        hr = User(email=f"{TAG}-hr@example.test", display_name="HR thử", role="HR")
        for user in (admin, hr):
            user.password_hash = hash_password(PASSWORD)
            session.add(user)
        await session.commit()
        result = SimpleNamespace(admin=admin.email, admin_id=admin.id, hr=hr.email, hr_id=hr.id)
    yield result
    async with session_factory() as session:
        team_ids = list((await session.scalars(select(Team.id).where(Team.code.like("ADMT%")))).all())
        user_ids = list((await session.scalars(select(User.id).where(User.email.like(f"{TAG}%")))).all())
        await session.execute(delete(JourneyTemplate).where(JourneyTemplate.created_by.in_(user_ids)))
        await session.execute(delete(TeamMember).where(TeamMember.team_id.in_(team_ids)))
        await session.execute(delete(TeamMember).where(TeamMember.user_id.in_(user_ids)))
        await session.execute(delete(AuditLog).where(AuditLog.actor_id.in_(user_ids)))
        await session.execute(delete(Team).where(Team.id.in_(team_ids)))
        await session.execute(delete(User).where(User.id.in_(user_ids)))
        await session.commit()


def client_for(session_factory: async_sessionmaker[AsyncSession]) -> httpx.AsyncClient:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    app: FastAPI = create_app()
    app.state.session_factory = session_factory
    app.state.login_throttle = LoginThrottle(3, 900)
    app.dependency_overrides[get_settings] = lambda: settings
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("10.0.0.1", 5000)), base_url="http://test")


async def test_hr_is_forbidden_from_admin_endpoints(
    session_factory: async_sessionmaker[AsyncSession], people: SimpleNamespace
) -> None:
    async with client_for(session_factory) as client:
        await client.post("/api/v1/auth/login", json={"email": people.hr, "password": PASSWORD})
        assert (await client.get("/api/v1/admin/users")).status_code == 403
        assert (await client.get("/api/v1/admin/dashboard")).status_code == 403


async def test_user_lifecycle_and_self_protection(
    session_factory: async_sessionmaker[AsyncSession], people: SimpleNamespace
) -> None:
    async with client_for(session_factory) as client:
        await client.post("/api/v1/auth/login", json={"email": people.admin, "password": PASSWORD})
        email = f"{TAG}-new@example.test"

        created = await client.post(
            "/api/v1/admin/users", json={"display_name": "Người mới", "email": email, "role": "USER"}
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["temporary_password"] and body["user"]["status"] == "ACTIVE"
        user_id = body["user"]["id"]

        dup = await client.post(
            "/api/v1/admin/users", json={"display_name": "Trùng", "email": email.upper(), "role": "USER"}
        )
        assert dup.status_code == 409 and dup.json()["code"] == "EMAIL_TAKEN"

        # đăng nhập bằng mật khẩu tạm rồi bị khóa thì không vào được nữa
        async with client_for(session_factory) as other:
            ok = await other.post("/api/v1/auth/login", json={"email": email, "password": body["temporary_password"]})
            assert ok.status_code == 200
        locked = await client.patch(f"/api/v1/admin/users/{user_id}/status", json={"status": "INACTIVE"})
        assert locked.json()["status"] == "INACTIVE"
        async with client_for(session_factory) as other:
            denied = await other.post(
                "/api/v1/auth/login", json={"email": email, "password": body["temporary_password"]}
            )
            assert denied.status_code in (401, 403)

        reset = await client.post(f"/api/v1/admin/users/{user_id}/reset-password")
        assert reset.status_code == 200 and reset.json()["temporary_password"] != body["temporary_password"]

        self_lock = await client.patch(f"/api/v1/admin/users/{people.admin_id}/status", json={"status": "INACTIVE"})
        assert self_lock.status_code == 409 and self_lock.json()["code"] == "CANNOT_LOCK_SELF"


async def test_team_membership_template_copy_and_audit(
    session_factory: async_sessionmaker[AsyncSession], people: SimpleNamespace
) -> None:
    async with client_for(session_factory) as client:
        await client.post("/api/v1/auth/login", json={"email": people.admin, "password": PASSWORD})

        # Tạo lộ trình mẫu chung (ADMIN → team_id NULL) rồi publish để có nguồn sao chép.
        template = (
            await client.post(
                "/api/v1/portal/journey-templates", json={"code": f"{TAG}-shared", "title": "Mẫu chung thử"}
            )
        ).json()
        stage = (
            await client.post(
                f"/api/v1/portal/journey-templates/{template['id']}/stages", json={"title": "Ngày 1", "sort_order": 1}
            )
        ).json()
        first = (
            await client.post(f"/api/v1/portal/stages/{stage['id']}/tasks", json={"title": "A", "body_markdown": "a"})
        ).json()
        await client.post(
            f"/api/v1/portal/stages/{stage['id']}/tasks",
            json={"title": "B", "body_markdown": "b", "depends_on": [first["id"]]},
        )
        assert (await client.post(f"/api/v1/portal/journey-templates/{template['id']}/publish")).status_code == 200

        code = f"ADMT{uuid4().hex[:6].upper()}"
        team = await client.post(
            "/api/v1/admin/teams",
            json={"name": "Phòng thử", "code": code, "hr_user_id": people.hr_id, "copy_shared_template": True},
        )
        assert team.status_code == 201, team.text
        team_json = team.json()
        assert team_json["hr_names"] == ["HR thử"]
        assert team_json["journey_title"] == "Mẫu chung thử" and team_json["journey_status"] == "DRAFT"

        # Chỉ HR mới làm "HR phụ trách"; trùng mã bị từ chối.
        bad_hr = await client.post(
            "/api/v1/admin/teams",
            json={"name": "X", "code": f"ADMT{uuid4().hex[:6].upper()}", "hr_user_id": people.admin_id},
        )
        assert bad_hr.status_code == 422 and bad_hr.json()["code"] == "NOT_AN_HR_USER"
        dup = await client.post("/api/v1/admin/teams", json={"name": "Y", "code": code})
        assert dup.status_code == 409 and dup.json()["code"] == "TEAM_CODE_TAKEN"

        member = await client.post(
            "/api/v1/admin/memberships", json={"team_id": team_json["id"], "user_id": people.hr_id}
        )
        assert member.status_code == 409 and member.json()["code"] == "ALREADY_MEMBER"

        archived = await client.patch(f"/api/v1/admin/teams/{team_json['id']}/status", json={"is_active": False})
        assert archived.json()["is_active"] is False
        rows = (await client.get("/api/v1/admin/memberships")).json()
        mine = next(r for r in rows if r["team_id"] == team_json["id"] and r["user_id"] == people.hr_id)
        assert mine["access"] == "BLOCKED_TEAM" and mine["team_role"] == "HR"

        again = await client.post(f"/api/v1/admin/teams/{team_json['id']}/copy-template")
        assert again.status_code == 409 and again.json()["code"] == "TEAM_ALREADY_HAS_JOURNEY"

        removed = await client.delete(f"/api/v1/admin/memberships/{team_json['id']}/{people.hr_id}")
        assert removed.status_code == 204

        logs = (await client.get("/api/v1/admin/audit-logs")).json()
        actions = {log["action"] for log in logs}
        assert {"CREATE_TEAM", "ARCHIVE_TEAM", "REMOVE_MEMBER"} <= actions

        overview = (await client.get("/api/v1/admin/template-overview")).json()
        assert overview["shared_template_id"] is not None and overview["shared_task_count"] >= 2
        dash = (await client.get("/api/v1/admin/dashboard")).json()
        assert dash["archived_teams"] >= 1
