"""Phụ thuộc dùng chung cho router (mở session DB, dựng service, xác thực và phân quyền)."""

from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass
from functools import lru_cache
from typing import Annotated, Any

from fastapi import Cookie, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.config import Settings, get_settings
from src.infrastructure.ai.chat_completion_port import ChatCompletionPort
from src.infrastructure.ai.deepseek_adapter import DeepSeekChatCompletion
from src.infrastructure.ai.fallback_chat_completion import CircuitBreaker, FallbackChatCompletion
from src.infrastructure.ai.llm_gate import shared_gate
from src.infrastructure.observability.call_metrics import set_user_id
from src.infrastructure.observability.langfuse_tracer import LangfuseTracer
from src.model.enums import UserRole
from src.model.team_member import TeamMember
from src.model.user import User
from src.services.auth.auth_service import load_session_user
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.sessions import SESSION_COOKIE_NAME, SessionError, SessionToken, read_token
from src.services.ingest.embedding.keep_warm import KeepWarm
from src.services.ingest.embedding.port import EmbeddingPort
from src.services.ingest.factory import build_embedding_port, build_storage_port
from src.services.ingest.storage import StoragePort
from src.services.readiness_service import ReadinessService
from src.services.viga.chat_throttle import ChatThrottle


def get_session_factory(request: Request) -> async_sessionmaker[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    return factory


async def get_db(request: Request) -> AsyncIterator[AsyncSession]:
    factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with factory() as session:
        yield session


def get_readiness_service(session: AsyncSession = Depends(get_db)) -> ReadinessService:
    return ReadinessService(session)


def get_keep_warm(request: Request) -> KeepWarm | None:
    """Bộ giữ ấm dịch vụ embedding; `None` khi không dùng dịch vụ thật hoặc đã tắt."""
    keep_warm: KeepWarm | None = getattr(request.app.state, "keep_warm", None)
    return keep_warm


def get_login_throttle(request: Request) -> LoginThrottle:
    throttle: LoginThrottle = request.app.state.login_throttle
    return throttle


def get_chat_throttle(request: Request) -> ChatThrottle:
    throttle: ChatThrottle = request.app.state.chat_throttle
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
    set_user_id(current.user.id)  # mỗi bản ghi llm_calls của request này mang user_id
    return current.user


def require_role(*roles: str) -> Callable[[User], Coroutine[Any, Any, User]]:
    """Dependency chỉ cho vai trò trong danh sách đi qua; trái vai trò thì `403 FORBIDDEN_ROLE`."""

    async def dependency(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise AuthError(403, "FORBIDDEN_ROLE", "auth.forbidden_role")
        return user

    return dependency


async def require_team_scope(team_id: int, user: User, db: AsyncSession) -> None:
    """Portal — plan-portal/P1/P1.md mục 3: 403 nếu `user` (role HR) không thuộc `team_id` đang truy cập.

    `ADMIN` luôn qua (quản trị kỹ thuật, không giới hạn theo phòng ban). Dùng `team_members` có sẵn
    (many-to-many, từ 0001_core) làm nguồn scope — không có cột `primary_team_id` riêng cho Portal.
    """
    if user.role == UserRole.ADMIN:
        return
    exists = await db.scalar(
        select(TeamMember.team_id).where(TeamMember.team_id == team_id, TeamMember.user_id == user.id)
    )
    if exists is None:
        raise AuthError(403, "FORBIDDEN_TEAM_SCOPE", "auth.forbidden_team_scope")


def get_embedding_port(settings: Annotated[Settings, Depends(get_settings)]) -> EmbeddingPort:
    return build_embedding_port(settings)


def get_storage_port(settings: Annotated[Settings, Depends(get_settings)]) -> StoragePort:
    return build_storage_port(settings)


@lru_cache
def _fallback_breaker(failure_threshold: int, cooldown_seconds: float) -> CircuitBreaker:
    """Một bộ ngắt mạch dùng chung cho cả tiến trình (cổng LLM được dựng lại mỗi yêu cầu nên không thể giữ trạng thái ở đó)."""
    return CircuitBreaker(failure_threshold=failure_threshold, cooldown_seconds=cooldown_seconds)


def get_chat_completion_port(settings: Annotated[Settings, Depends(get_settings)]) -> ChatCompletionPort:
    if settings.llm_api_key is None:
        raise RuntimeError("LLM_API_KEY chưa cấu hình")
    primary = DeepSeekChatCompletion(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key.get_secret_value(),
        model=settings.llm_model,
        max_retries=settings.llm_max_retries,
        gate=shared_gate(settings.llm_max_concurrent, settings.llm_background_max_concurrent),
    )
    if not (settings.llm_fallback_enabled and settings.llm_fallback_api_key is not None):
        return primary
    secondary = DeepSeekChatCompletion(
        base_url=settings.llm_fallback_base_url,
        api_key=settings.llm_fallback_api_key.get_secret_value(),
        model=settings.llm_fallback_model,
        timeout_seconds=settings.llm_fallback_timeout_seconds,
        max_retries=1,
        gate=shared_gate(settings.llm_max_concurrent, settings.llm_background_max_concurrent),
        provider_name="fallback",
        reasoning_style="openrouter",
        json_mode=False,
        supports_stream=False,
        max_output_tokens=settings.llm_fallback_max_output_tokens,
    )
    return FallbackChatCompletion(
        primary,
        secondary,
        _fallback_breaker(settings.llm_fallback_failure_threshold, settings.llm_fallback_cooldown_seconds),
        allow_background=settings.llm_fallback_for_background,
    )


def get_optional_chat_completion_port(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ChatCompletionPort | None:
    """Như `get_chat_completion_port` nhưng thiếu khóa thì trả None thay vì lỗi: Viga vẫn trả lời được bằng luật và công cụ
    lộ trình, chỉ phần cần LLM mới báo "tạm thời chưa trả lời được"."""
    if settings.llm_api_key is None:
        return None
    return get_chat_completion_port(settings)


def get_langfuse_tracer(request: Request) -> LangfuseTracer:
    tracer: LangfuseTracer = request.app.state.langfuse_tracer
    return tracer
