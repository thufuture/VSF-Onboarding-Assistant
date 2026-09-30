"""`/api/v1/auth/*`: đăng nhập, đăng xuất, hồ sơ phiên, gia hạn."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import (
    AuthenticatedSession,
    get_current_session,
    get_db,
    get_login_throttle,
    session_secret,
)
from src.config import Settings, get_settings
from src.dto.request.auth_request_dto import LoginRequestDTO
from src.dto.response.auth_response_dto import SessionUserResponseDTO
from src.dto.response.error_response_dto import ErrorResponseDTO
from src.model.user import User
from src.services.auth.auth_service import (
    authenticate,
    department_name,
    load_session_user,
    revoke_sessions,
    start_session,
)
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.sessions import SESSION_COOKIE_NAME, SessionError, read_token, should_refresh

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

_ERRORS: dict[int | str, dict[str, object]] = {
    401: {"model": ErrorResponseDTO},
    403: {"model": ErrorResponseDTO},
    429: {"model": ErrorResponseDTO},
}


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        samesite="lax",
        # localhost chạy HTTP nên chỉ bắt buộc Secure ở production (sau Caddy/HTTPS).
        secure=settings.app_env == "production",
        path="/",
    )


async def _profile(db: AsyncSession, user: User, expires_at_seconds: int) -> SessionUserResponseDTO:
    return SessionUserResponseDTO.model_validate(
        {
            "id": user.id,
            "email": user.email,
            "display_name": user.display_name,
            "role": user.role,
            "department": await department_name(db, user.id),
            "expires_at": datetime.fromtimestamp(expires_at_seconds, UTC),
        }
    )


@router.post("/login", response_model=SessionUserResponseDTO, responses=_ERRORS)
async def login(
    body: LoginRequestDTO,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    throttle: Annotated[LoginThrottle, Depends(get_login_throttle)],
) -> SessionUserResponseDTO:
    client_ip = request.client.host if request.client else "unknown"
    user = await authenticate(db, email=body.email, password=body.password, client_ip=client_ip, throttle=throttle)
    token, expires_at = start_session(user, session_secret(settings), settings.session_ttl_seconds)
    set_session_cookie(response, token, settings)
    return await _profile(db, user, expires_at)


@router.get("/me", response_model=SessionUserResponseDTO, responses=_ERRORS)
async def me(
    current: Annotated[AuthenticatedSession, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionUserResponseDTO:
    return await _profile(db, current.user, current.token.expires_at)


@router.post("/refresh", response_model=SessionUserResponseDTO, responses=_ERRORS)
async def refresh(
    response: Response,
    current: Annotated[AuthenticatedSession, Depends(get_current_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionUserResponseDTO:
    """Gia hạn phiên cho người đang dùng; chỉ cấp cookie mới khi phiên đã dùng quá nửa thời hạn."""
    if not should_refresh(current.token, settings.session_ttl_seconds):
        return await _profile(db, current.user, current.token.expires_at)
    token, expires_at = start_session(current.user, session_secret(settings), settings.session_ttl_seconds)
    set_session_cookie(response, token, settings)
    return await _profile(db, current.user, expires_at)


@router.post("/logout", status_code=204)
async def logout(
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    vsf_session: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> Response:
    """Xóa cookie **và** thu hồi mọi phiên của người dùng (cookie cũ bị từ chối ngay); gọi lại vẫn `204`."""
    if vsf_session:
        try:
            token = read_token(vsf_session, session_secret(settings))
            user = await load_session_user(db, token)
        except (SessionError, AuthError):
            pass  # token hỏng, hết hạn hoặc đã thu hồi: không còn gì để thu hồi, chỉ xóa cookie
        else:
            await revoke_sessions(db, user)
    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/", httponly=True, samesite="lax")
    return response
