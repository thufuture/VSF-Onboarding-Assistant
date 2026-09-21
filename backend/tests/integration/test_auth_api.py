"""Luồng xác thực đầu-cuối trên PostgreSQL thật: đăng nhập, đăng xuất, thu hồi, giới hạn thử sai, phân quyền."""

import json
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import Depends, FastAPI
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.api.dependencies import require_role
from src.config import Settings, get_settings
from src.infrastructure.persistence.engine import create_session_factory
from src.main import create_app
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import hash_password, verify_password
from src.services.auth.seed import DEV_EMAIL_DOMAIN, assert_no_dev_accounts, count_dev_accounts, seed_reference_users
from src.services.auth.sessions import SESSION_COOKIE_NAME, issue_token

pytestmark = pytest.mark.integration

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
PASSWORD = "ChangeMe!123"

MakeUser = Callable[..., Awaitable[SimpleNamespace]]


@pytest.fixture
async def session_factory(migrated_database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(migrated_database_url)
    try:
        yield create_session_factory(engine)
    finally:
        await engine.dispose()


@pytest.fixture
async def make_user(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[MakeUser]:
    """Tạo người dùng đã commit (app dùng kết nối riêng) và dọn sạch sau test."""
    created: list[str] = []

    async def make(
        role: str = "USER", status: str = "ACTIVE", password: str = PASSWORD, name: str = "Người Thử"
    ) -> Any:
        email = f"auth-{uuid4().hex[:10]}@example.test"
        async with session_factory() as session:
            user = User(email=email, display_name=name, role=role, status=status, password_hash=hash_password(password))
            session.add(user)
            await session.commit()
            created.append(email)
            return SimpleNamespace(email=email, password=password, id=user.id, role=role)

    yield make
    async with session_factory() as session:
        await session.execute(delete(User).where(User.email.in_(created)))
        await session.commit()


@pytest.fixture
def app(session_factory: async_sessionmaker[AsyncSession]) -> FastAPI:
    settings = Settings(_env_file=None, session_secret=SECRET, login_max_failures=3, login_window_seconds=900)
    application = create_app()
    application.state.session_factory = session_factory
    application.state.login_throttle = LoginThrottle(3, 900)
    application.dependency_overrides[get_settings] = lambda: settings

    @application.get("/_test/staff", dependencies=[Depends(require_role("HR", "ADMIN"))])
    async def staff_only() -> dict[str, str]:
        return {"ok": "yes"}

    return application


def client_for(app: FastAPI, ip: str = "10.0.0.1") -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app, client=(ip, 5000))
    return httpx.AsyncClient(transport=transport, base_url="http://test")


def client_with_cookie(app: FastAPI, value: str, ip: str = "10.0.0.1") -> httpx.AsyncClient:
    client = client_for(app, ip)
    client.cookies.set(SESSION_COOKIE_NAME, value)
    return client


async def login(client: httpx.AsyncClient, user: SimpleNamespace, password: str | None = None) -> httpx.Response:
    return await client.post("/api/v1/auth/login", json={"email": user.email, "password": password or user.password})


# ---- đăng nhập ----


async def test_login_sets_an_httponly_cookie_and_returns_the_profile(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user(role="HR", name="Nhân sự HR")
    async with client_for(app) as client:
        response = await login(client, user)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"id", "email", "display_name", "role", "department", "expires_at"}
    assert body["department"] is None  # chưa thuộc đội nào
    assert body["email"] == user.email and body["role"] == "HR" and body["display_name"] == "Nhân sự HR"
    cookie = response.headers["set-cookie"].lower()
    assert f"{SESSION_COOKIE_NAME}=" in cookie
    assert "httponly" in cookie and "samesite=lax" in cookie and "path=/" in cookie
    assert "secure" not in cookie  # localhost chạy HTTP; production mới bật Secure


async def test_profile_reports_the_department_from_team_membership(
    app: FastAPI, make_user: MakeUser, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await make_user()
    code = f"T{uuid4().hex[:8]}"
    async with session_factory() as session:
        team_a = Team(code=f"{code}A", name="Zeta Team")
        team_b = Team(code=f"{code}B", name="Alpha Team")
        inactive = Team(code=f"{code}C", name="Ẩn", is_active=False)
        session.add_all([team_a, team_b, inactive])
        await session.flush()
        session.add_all([TeamMember(team_id=t.id, user_id=user.id) for t in (team_a, team_b, inactive)])
        await session.commit()
        team_ids = [team_a.id, team_b.id, inactive.id]
    try:
        async with client_for(app) as client:
            logged_in = await login(client, user)
            me = await client.get("/api/v1/auth/me")
        # Nhiều đội thì nối theo tên; đội đã tắt không hiện.
        assert logged_in.json()["department"] == "Alpha Team, Zeta Team"
        assert me.json()["department"] == "Alpha Team, Zeta Team"
    finally:
        async with session_factory() as session:
            await session.execute(delete(TeamMember).where(TeamMember.user_id == user.id))
            await session.execute(delete(Team).where(Team.id.in_(team_ids)))
            await session.commit()


async def test_login_is_case_insensitive_for_email(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        response = await client.post(
            "/api/v1/auth/login", json={"email": f"  {user.email.upper()}  ", "password": user.password}
        )
    assert response.status_code == 200


async def test_wrong_password_and_unknown_email_are_indistinguishable(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        wrong = await login(client, user, "sai-mat-khau")
        unknown = await client.post("/api/v1/auth/login", json={"email": "khong-co@example.test", "password": "x"})
    assert wrong.status_code == unknown.status_code == 401
    assert (
        wrong.json()
        == unknown.json()
        == {
            "code": "INVALID_CREDENTIALS",
            "message_key": "auth.invalid_credentials",
            "detail": None,
        }
    )
    assert SESSION_COOKIE_NAME not in wrong.headers.get("set-cookie", "")


async def test_inactive_account_is_rejected_only_with_the_right_password(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user(status="INACTIVE")
    async with client_for(app) as client:
        blocked = await login(client, user)
        wrong = await login(client, user, "sai-mat-khau")
    assert blocked.status_code == 403 and blocked.json()["code"] == "ACCOUNT_INACTIVE"
    assert wrong.status_code == 401  # không lộ trạng thái tài khoản khi chưa biết mật khẩu


async def test_login_body_is_validated(app: FastAPI) -> None:
    async with client_for(app) as client:
        response = await client.post("/api/v1/auth/login", json={"email": "a@b.co"})
    assert response.status_code == 422


async def test_login_updates_last_login_at(
    app: FastAPI, make_user: MakeUser, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    user = await make_user()
    async with client_for(app) as client:
        await login(client, user)
    async with session_factory() as session:
        stored = await session.get(User, user.id)
    assert stored is not None and stored.last_login_at is not None


# ---- giới hạn thử sai ----


async def test_login_is_throttled_after_repeated_failures_even_for_the_right_password(
    app: FastAPI, make_user: MakeUser
) -> None:
    user = await make_user()
    async with client_for(app) as client:
        for _ in range(3):
            assert (await login(client, user, "sai")).status_code == 401
        blocked = await login(client, user)  # đúng mật khẩu nhưng đã bị chặn
    assert blocked.status_code == 429
    assert blocked.json()["code"] == "TOO_MANY_ATTEMPTS"
    assert 0 < int(blocked.headers["retry-after"]) <= 900


async def test_throttle_is_per_ip_and_success_resets_the_counter(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app, "10.0.0.1") as attacker:
        for _ in range(3):
            await login(attacker, user, "sai")
        assert (await login(attacker, user)).status_code == 429
    async with client_for(app, "10.0.0.2") as owner:
        assert (await login(owner, user)).status_code == 200  # chủ tài khoản ở IP khác không bị khóa hộ
        for _ in range(2):
            await login(owner, user, "sai")
        assert (await login(owner, user)).status_code == 200  # đăng nhập đúng xóa bộ đếm
        for _ in range(2):
            await login(owner, user, "sai")
        assert (await login(owner, user, "sai")).status_code == 401  # vẫn chưa chạm ngưỡng


# ---- hồ sơ phiên ----


async def test_me_requires_a_valid_session(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        anonymous = await client.get("/api/v1/auth/me")
        assert anonymous.status_code == 401 and anonymous.json()["code"] == "UNAUTHENTICATED"
        await login(client, user)
        profile = await client.get("/api/v1/auth/me")
    assert profile.status_code == 200 and profile.json()["email"] == user.email


async def test_tampered_and_expired_cookies_are_rejected(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        await login(client, user)
        good = client.cookies[SESSION_COOKIE_NAME]
    expired = issue_token(user.id, SECRET, ttl_seconds=60, issued_at_ms=int(time.time() * 1000) - 3_600_000)
    other_user = issue_token(user.id + 1, SECRET, ttl_seconds=60).rsplit(".", 1)[0] + "." + good.rsplit(".", 1)[1]
    results: dict[str, httpx.Response] = {}
    for name, value in {
        "tampered": good[:-2] + "00",
        "expired": expired,
        "other user with stolen signature": other_user,
    }.items():
        async with client_with_cookie(app, value) as anonymous:
            results[name] = await anonymous.get("/api/v1/auth/me")
    assert {name: response.status_code for name, response in results.items()} == dict.fromkeys(results, 401)
    assert results["expired"].json()["code"] == "SESSION_EXPIRED"


async def test_the_dev_header_shortcut_does_not_exist(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        response = await client.get("/api/v1/auth/me", headers={"X-User-Id": str(user.id)})
    assert response.status_code == 401


# ---- đăng xuất và thu hồi ----


async def test_logout_revokes_the_old_cookie_immediately(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        await login(client, user)
        old_cookie = client.cookies[SESSION_COOKIE_NAME]
        response = await client.post("/api/v1/auth/logout")
        assert response.status_code == 204
        assert (
            "max-age=0" in response.headers["set-cookie"].lower()
            or "expires=" in response.headers["set-cookie"].lower()
        )
    async with client_with_cookie(app, old_cookie) as replay:
        stolen = await replay.get("/api/v1/auth/me")
    assert stolen.status_code == 401 and stolen.json()["code"] == "SESSION_REVOKED"


async def test_logout_kills_every_session_of_the_user(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as laptop, client_for(app) as phone:
        await login(laptop, user)
        await login(phone, user)
        await laptop.post("/api/v1/auth/logout")
        assert (await phone.get("/api/v1/auth/me")).status_code == 401


async def test_login_right_after_logout_works_immediately(app: FastAPI, make_user: MakeUser) -> None:
    """Lỗi từng gặp ở Ralion: đăng xuất/đổi mật khẩu xong đăng nhập lại vẫn bị đá ra."""
    user = await make_user()
    async with client_for(app) as client:
        for _ in range(3):
            assert (await login(client, user)).status_code == 200
            assert (await client.get("/api/v1/auth/me")).status_code == 200
            assert (await client.post("/api/v1/auth/logout")).status_code == 204
            assert (await client.get("/api/v1/auth/me")).status_code == 401


async def test_logout_without_or_with_a_bad_session_is_still_204(app: FastAPI) -> None:
    async with client_for(app) as client:
        assert (await client.post("/api/v1/auth/logout")).status_code == 204
    async with client_with_cookie(app, "rac.roi.khong.hop-le") as client:
        assert (await client.post("/api/v1/auth/logout")).status_code == 204


async def test_a_session_is_rejected_after_the_account_is_blocked_or_revoked_directly(
    app: FastAPI, make_user: MakeUser, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    blocked, revoked = await make_user(), await make_user()
    async with client_for(app) as first, client_for(app) as second:
        await login(first, blocked)
        await login(second, revoked)
        async with session_factory() as session:
            await session.execute(update(User).where(User.id == blocked.id).values(status="INACTIVE"))
            await session.execute(
                update(User)
                .where(User.id == revoked.id)
                .values(session_invalid_before=None)  # chưa thu hồi thì còn sống
            )
            await session.commit()
        assert (await first.get("/api/v1/auth/me")).status_code == 401
        assert (await second.get("/api/v1/auth/me")).status_code == 200
        async with session_factory() as session:
            from src.services.auth.sessions import revocation_stamp

            await session.execute(
                update(User).where(User.id == revoked.id).values(session_invalid_before=revocation_stamp())
            )
            await session.commit()
        assert (await second.get("/api/v1/auth/me")).status_code == 401


# ---- gia hạn ----


async def test_refresh_only_renews_an_aged_session(app: FastAPI, make_user: MakeUser) -> None:
    user = await make_user()
    async with client_for(app) as client:
        fresh = await login(client, user)
        untouched = await client.post("/api/v1/auth/refresh")
        assert untouched.status_code == 200
        assert "set-cookie" not in untouched.headers  # phiên còn mới: không ghi cookie
        assert untouched.json()["expires_at"] == fresh.json()["expires_at"]

    aged = issue_token(user.id, SECRET, ttl_seconds=1800, issued_at_ms=int(time.time() * 1000) - 20 * 60 * 1000)
    async with client_with_cookie(app, aged) as client:
        renewed = await client.post("/api/v1/auth/refresh")
    assert renewed.status_code == 200
    assert SESSION_COOKIE_NAME in renewed.headers["set-cookie"]
    # Hạn mới tính từ bây giờ (không phải từ lúc token cũ được cấp cách đây 20 phút).
    assert datetime.fromisoformat(renewed.json()["expires_at"]) >= datetime.fromisoformat(fresh.json()["expires_at"])
    assert datetime.fromisoformat(renewed.json()["expires_at"]) > datetime.now(UTC) + timedelta(minutes=25)

    dead = issue_token(user.id, SECRET, ttl_seconds=60, issued_at_ms=int(time.time() * 1000) - 3_600_000)
    async with client_with_cookie(app, dead) as client:
        assert (await client.post("/api/v1/auth/refresh")).status_code == 401


# ---- vai trò ----


async def test_role_guard(app: FastAPI, make_user: MakeUser) -> None:
    staff, member = await make_user(role="HR"), await make_user(role="USER")
    async with client_for(app) as anonymous, client_for(app) as hr, client_for(app) as user:
        assert (await anonymous.get("/_test/staff")).status_code == 401
        await login(hr, staff)
        await login(user, member)
        assert (await hr.get("/_test/staff")).status_code == 200
        forbidden = await user.get("/_test/staff")
    assert forbidden.status_code == 403 and forbidden.json()["code"] == "FORBIDDEN_ROLE"


# ---- nạp tài khoản dev ----


async def test_seed_creates_teams_users_and_memberships_idempotently(
    session_factory: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    tag = uuid4().hex[:8].upper()
    (tmp_path / "teams.json").write_text(
        json.dumps([{"code": f"SEEDT_{tag}", "name": "Đội thử", "ticket_prefix": None, "description": "test"}]),
        encoding="utf-8",
    )
    email = f"seedtest-{tag.lower()}{DEV_EMAIL_DOMAIN}"
    (tmp_path / "users.json").write_text(
        json.dumps(
            [
                {
                    "email": email.upper(),
                    "display_name": "Tài khoản dev",
                    "role": "HR",
                    "teams": [f"SEEDT_{tag}"],
                    "password_dev_only": PASSWORD,
                }
            ]
        ),
        encoding="utf-8",
    )
    try:
        async with session_factory() as session:
            first = await seed_reference_users(session, tmp_path)
        async with session_factory() as session:
            second = await seed_reference_users(session, tmp_path)
            user = await session.scalar(select(User).where(User.email == email))
            dev_count = await count_dev_accounts(session)
            with pytest.raises(RuntimeError, match="tài khoản dev"):
                await assert_no_dev_accounts(session)
        assert (first.teams_created, first.users_created, first.memberships_created) == (1, 1, 1)
        assert (second.teams_created, second.users_created, second.memberships_created) == (0, 0, 0)
        assert user is not None and user.role == "HR" and verify_password(PASSWORD, user.password_hash)
        assert dev_count >= 1
    finally:
        async with session_factory() as session:
            found = await session.scalar(select(User).where(User.email == email))
            team = await session.scalar(select(Team).where(Team.code == f"SEEDT_{tag}"))
            if found is not None and team is not None:
                await session.execute(delete(TeamMember).where(TeamMember.user_id == found.id))
            if found is not None:
                await session.execute(delete(User).where(User.id == found.id))
            if team is not None:
                await session.execute(delete(Team).where(Team.id == team.id))
            await session.commit()
