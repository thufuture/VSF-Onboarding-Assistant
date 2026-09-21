"""Phụ thuộc dùng chung cho router (mở session DB, dựng service, xác thực và phân quyền)."""

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Cookie, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import Settings, get_settings
from src.model.user import User
from src.services.auth.auth_service import load_session_user
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.sessions import SESSION_COOKIE_NAME, SessionError, SessionToken, read_token
from src.services.readiness_service import ReadinessService


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_readiness_service(session: AsyncSession = Depends(get_db)) -> ReadinessService:
    return ReadinessService(session)


def get_login_throttle(request: Request) -> LoginThrottle:
    throttle: LoginThrottle = request.app.state.login_throttle
    return throttle


def session_secret(settings: Settings) -> str:
    # Settings luôn có khóa (tự sinh ngoài production, bắt buộc ở production): xem Settings._session_secret_rules.
    assert settings.session_secret is not None
    return settings.session_secret.get_secret_value()


@dataclass(frozen=True)
class AuthenticatedSession:
    user: User
    token: SessionToken


async def get_current_session(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    vsf_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> AuthenticatedSession:
    """Danh tính của request: **chỉ** từ cookie phiên có chữ ký (không có lối tắt qua header như `X-User-Id`)."""
    try:
        token = read_token(vsf_session, session_secret(settings))
    except SessionError as exc:
        raise AuthError(401, exc.code, exc.message_key) from exc
    user = await load_session_user(db, token)
    return AuthenticatedSession(user=user, token=token)


async def get_current_user(current: Annotated[AuthenticatedSession, Depends(get_current_session)]) -> User:
    return current.user


def require_role(*roles: str) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency chỉ cho vai trò trong danh sách đi qua; trái vai trò thì `403 FORBIDDEN_ROLE`."""

    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise AuthError(403, "FORBIDDEN_ROLE", "auth.forbidden_role")
        return user

    return dependency
