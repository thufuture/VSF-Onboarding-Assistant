"""Đăng nhập, kiểm phiên và thu hồi phiên."""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.model.enums import UserStatus
from src.model.user import User
from src.services.auth.errors import AuthError
from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import dummy_hash, verify_password
from src.services.auth.sessions import (
    SessionToken,
    is_revoked,
    issue_token,
    next_issue_ms,
    now_ms,
    revocation_stamp,
)


def normalize_email(email: str) -> str:
    return email.strip().lower()


async def authenticate(
    session: AsyncSession,
    *,
    email: str,
    password: str,
    client_ip: str,
    throttle: LoginThrottle,
) -> User:
    """Kiểm email và mật khẩu; ném `AuthError` (401/403/429) nếu không hợp lệ.

    - Giới hạn thử sai kiểm **trước** khi băm mật khẩu (kẻ tấn công không được bắt máy chủ làm việc nặng vô hạn).
    - Email không tồn tại vẫn băm một chuỗi giả nên thời gian phản hồi gần như nhau; cùng một thông báo cho email lạ và
      mật khẩu sai.
    - Tài khoản bị khóa chỉ lộ ra khi mật khẩu đúng.
    """
    normalized = normalize_email(email)
    key = f"{normalized}|{client_ip}"
    wait = throttle.retry_after(key)
    if wait > 0:
        raise AuthError(429, "TOO_MANY_ATTEMPTS", "auth.too_many_attempts", headers={"Retry-After": str(wait)})

    user = await session.scalar(select(User).where(func.lower(User.email) == normalized))
    password_ok = verify_password(password, user.password_hash if user else dummy_hash())
    if user is None or not password_ok:
        throttle.record_failure(key)
        raise AuthError(401, "INVALID_CREDENTIALS", "auth.invalid_credentials")
    if user.status != UserStatus.ACTIVE:
        raise AuthError(403, "ACCOUNT_INACTIVE", "auth.account_inactive")

    throttle.reset(key)
    user.last_login_at = datetime.now(UTC)
    await session.commit()
    return user


def start_session(user: User, secret: str, ttl_seconds: int) -> tuple[str, int]:
    """Cấp token mới cho người dùng; trả về (token, expires_at giây)."""
    issued = next_issue_ms(user.session_invalid_before)
    token = issue_token(user.id, secret, ttl_seconds=ttl_seconds, issued_at_ms=issued)
    return token, issued // 1000 + ttl_seconds


async def load_session_user(session: AsyncSession, token: SessionToken) -> User:
    """Nạp người dùng của phiên; từ chối nếu không còn tồn tại, bị khóa hoặc phiên đã bị thu hồi."""
    user = await session.get(User, token.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthError(401, "SESSION_INVALID", "auth.session_invalid")
    if is_revoked(token.issued_at_ms, user.session_invalid_before):
        raise AuthError(401, "SESSION_REVOKED", "auth.session_revoked")
    return user


async def revoke_sessions(session: AsyncSession, user: User) -> None:
    """Thu hồi mọi phiên của người dùng (mọi cookie phát hành trước lúc này đều bị từ chối)."""
    # +1 ms: token cấp trong cùng mili giây với lúc thu hồi cũng phải chết (token mới luôn được cấp sau mốc này).
    user.session_invalid_before = revocation_stamp(now_ms() + 1)
    await session.commit()
