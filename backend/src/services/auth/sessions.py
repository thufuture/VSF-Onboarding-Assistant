"""Phiên đăng nhập bằng cookie ký HMAC, không có bảng `sessions`.

Token là chuỗi tự chứa `user_id.issued_at_ms.expires_at.chữ_ký` (chép ý tưởng từ Ralion, đổi tên cookie). Mọi request
chỉ tốn một phép so sánh HMAC; thu hồi tức thì bằng cột `users.session_invalid_before`: token phát hành **trước** mốc
này bị từ chối.

Khác Ralion: thời điểm phát hành lưu bằng **mili giây** và mốc thu hồi cũng chính xác tới mili giây. Ralion cắt xuống
giây nên token phát hành cùng giây với lúc thu hồi vẫn sống (đăng xuất xong dùng lại cookie cũ trong cùng giây vẫn
qua). Ở đây token cũ luôn chết, còn token cấp sau đăng nhập lại luôn sống nhờ `next_issue_ms` (không bao giờ phát hành
sớm hơn mốc thu hồi).
"""

import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

SESSION_COOKIE_NAME = "vsf_session"

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)
_MS = timedelta(milliseconds=1)


class SessionError(Exception):
    """Token thiếu, sai định dạng, sai chữ ký hoặc hết hạn."""

    def __init__(self, code: str, message_key: str) -> None:
        super().__init__(code)
        self.code = code
        self.message_key = message_key


@dataclass(frozen=True)
class SessionToken:
    user_id: int
    issued_at_ms: int
    expires_at: int  # giây kể từ epoch


def now_ms() -> int:
    return time.time_ns() // 1_000_000


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(user_id: int, secret: str, *, ttl_seconds: int, issued_at_ms: int | None = None) -> str:
    issued = now_ms() if issued_at_ms is None else issued_at_ms
    expires_at = issued // 1000 + ttl_seconds
    payload = f"{user_id}.{issued}.{expires_at}"
    return f"{payload}.{_sign(payload, secret)}"


def read_token(token: str | None, secret: str, *, current_ms: int | None = None) -> SessionToken:
    """Kiểm chữ ký (so sánh không rò thời gian) **trước** khi tin bất kỳ trường nào, rồi kiểm hạn."""
    if not token:
        raise SessionError("UNAUTHENTICATED", "auth.unauthenticated")
    parts = token.split(".")
    if len(parts) != 4:
        raise SessionError("SESSION_MALFORMED", "auth.session_invalid")
    raw_user, raw_issued, raw_expires, signature = parts
    if not hmac.compare_digest(_sign(f"{raw_user}.{raw_issued}.{raw_expires}", secret), signature):
        raise SessionError("SESSION_INVALID_SIGNATURE", "auth.session_invalid")
    try:
        user_id, issued_at_ms, expires_at = int(raw_user), int(raw_issued), int(raw_expires)
    except ValueError as exc:
        raise SessionError("SESSION_MALFORMED", "auth.session_invalid") from exc
    current = now_ms() if current_ms is None else current_ms
    if current >= expires_at * 1000:
        raise SessionError("SESSION_EXPIRED", "auth.session_expired")
    return SessionToken(user_id=user_id, issued_at_ms=issued_at_ms, expires_at=expires_at)


def revocation_stamp(current_ms: int | None = None) -> datetime:
    """Mốc ghi vào `users.session_invalid_before` (chính xác tới mili giây, có múi giờ)."""
    moment = now_ms() if current_ms is None else current_ms
    return _EPOCH + moment * _MS


def _to_ms(moment: datetime) -> int:
    return (moment.astimezone(UTC) - _EPOCH) // _MS


def is_revoked(issued_at_ms: int, invalid_before: datetime | None) -> bool:
    """Token phát hành trước mốc thu hồi thì không còn hợp lệ; `None` là chưa từng thu hồi."""
    if invalid_before is None:
        return False
    return issued_at_ms < _to_ms(invalid_before)


def next_issue_ms(invalid_before: datetime | None, current_ms: int | None = None) -> int:
    """Thời điểm phát hành cho token mới: không bao giờ sớm hơn mốc thu hồi (nếu không token mới bị chính nó giết)."""
    moment = now_ms() if current_ms is None else current_ms
    if invalid_before is None:
        return moment
    return max(moment, _to_ms(invalid_before) + 1)


def should_refresh(token: SessionToken, ttl_seconds: int, *, current_ms: int | None = None) -> bool:
    """Chỉ gia hạn khi phiên đã dùng quá một nửa thời hạn, để không ghi cookie mới ở mỗi request."""
    moment = now_ms() if current_ms is None else current_ms
    return token.expires_at * 1000 - moment < ttl_seconds * 1000 // 2


def expires_at_datetime(token: SessionToken) -> datetime:
    return datetime.fromtimestamp(token.expires_at, UTC)
