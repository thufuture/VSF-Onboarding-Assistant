import pytest

from src.services.auth.login_throttle import LoginThrottle
from src.services.auth.passwords import dummy_hash, hash_password, verify_password
from src.services.auth.sessions import (
    SessionError,
    is_revoked,
    issue_token,
    next_issue_ms,
    read_token,
    revocation_stamp,
    should_refresh,
)

SECRET = "f3b1c9d2a7e84f6b95a0c3d1e7b28a4f6d0c9e5b1a3f7d2c"
TTL = 1800
NOW = 1_800_000_000_000  # mili giây


# ---- mật khẩu ----


def test_password_roundtrip_and_salting() -> None:
    first, second = hash_password("ChangeMe!123"), hash_password("ChangeMe!123")
    assert first != second  # mỗi lần một salt riêng
    assert verify_password("ChangeMe!123", first)
    assert verify_password("ChangeMe!123", second)
    assert not verify_password("changeme!123", first)


@pytest.mark.parametrize("encoded", [None, "", "plain", "scrypt$zz$zz", "bcrypt$00$00", "scrypt$00"])
def test_verify_rejects_missing_or_malformed_hashes(encoded: str | None) -> None:
    assert verify_password("anything", encoded) is False


def test_dummy_hash_is_well_formed_and_never_matches_real_passwords() -> None:
    assert dummy_hash().startswith("scrypt$")
    assert not verify_password("ChangeMe!123", dummy_hash())


# ---- token phiên ----


def test_token_roundtrip() -> None:
    token = issue_token(42, SECRET, ttl_seconds=TTL, issued_at_ms=NOW)
    parsed = read_token(token, SECRET, current_ms=NOW + 1000)
    assert parsed.user_id == 42
    assert parsed.issued_at_ms == NOW
    assert parsed.expires_at == NOW // 1000 + TTL


def test_token_is_rejected_when_expired() -> None:
    token = issue_token(1, SECRET, ttl_seconds=TTL, issued_at_ms=NOW)
    read_token(token, SECRET, current_ms=NOW + (TTL - 1) * 1000)  # còn hạn
    with pytest.raises(SessionError) as excinfo:
        read_token(token, SECRET, current_ms=NOW + TTL * 1000 + 1000)
    assert excinfo.value.code == "SESSION_EXPIRED"


def _forge(kind: str) -> str:
    token = issue_token(7, SECRET, ttl_seconds=TTL, issued_at_ms=NOW)
    user, issued, expires, signature = token.split(".")
    return {
        "another_user": f"8.{issued}.{expires}.{signature}",
        "later_expiry": f"{user}.{issued}.{int(expires) + 99999}.{signature}",
        "zero_signature": f"{user}.{issued}.{expires}.{'0' * len(signature)}",
        "last_char_changed": token[:-1] + ("0" if token[-1] != "0" else "1"),
    }[kind]


@pytest.mark.parametrize("kind", ["another_user", "later_expiry", "zero_signature", "last_char_changed"])
def test_tampered_tokens_are_rejected(kind: str) -> None:
    with pytest.raises(SessionError) as excinfo:
        read_token(_forge(kind), SECRET, current_ms=NOW)
    assert excinfo.value.code == "SESSION_INVALID_SIGNATURE"


def test_token_signed_with_another_secret_is_rejected() -> None:
    token = issue_token(1, "another-secret-another-secret-another-secret", ttl_seconds=TTL, issued_at_ms=NOW)
    with pytest.raises(SessionError):
        read_token(token, SECRET, current_ms=NOW)


@pytest.mark.parametrize("token", [None, "", "a.b.c", "a.b.c.d.e", "x.y.z.w"])
def test_missing_or_malformed_tokens_are_rejected(token: str | None) -> None:
    with pytest.raises(SessionError):
        read_token(token, SECRET, current_ms=NOW)


def test_non_numeric_fields_with_a_valid_signature_are_still_rejected() -> None:
    import hashlib
    import hmac

    payload = "abc.def.ghi"
    signature = hmac.new(SECRET.encode(), payload.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(SessionError) as excinfo:
        read_token(f"{payload}.{signature}", SECRET, current_ms=NOW)
    assert excinfo.value.code == "SESSION_MALFORMED"


# ---- thu hồi ----


def test_tokens_issued_before_the_revocation_stamp_are_revoked() -> None:
    stamp = revocation_stamp(NOW + 5)
    assert is_revoked(NOW, stamp)
    assert is_revoked(NOW + 4, stamp)


def test_no_revocation_stamp_means_never_revoked() -> None:
    assert is_revoked(NOW, None) is False


def test_a_token_issued_after_revocation_survives_even_in_the_same_millisecond() -> None:
    """Lỗi từng gặp ở Ralion: đăng xuất xong đăng nhập lại ngay vẫn bị đá ra vì cắt giây."""
    stamp = revocation_stamp(NOW)
    fresh_ms = next_issue_ms(stamp, current_ms=NOW)  # đồng hồ chưa nhích so với lúc thu hồi
    assert fresh_ms > NOW
    assert is_revoked(fresh_ms, stamp) is False
    # còn token cũ cấp trước đó vẫn chết
    assert is_revoked(NOW - 1, stamp)


def test_next_issue_time_is_simply_now_when_the_clock_has_moved_on() -> None:
    stamp = revocation_stamp(NOW)
    assert next_issue_ms(stamp, current_ms=NOW + 500) == NOW + 500
    assert next_issue_ms(None, current_ms=NOW) == NOW


def test_refresh_only_after_half_of_the_lifetime() -> None:
    token = read_token(issue_token(1, SECRET, ttl_seconds=TTL, issued_at_ms=NOW), SECRET, current_ms=NOW)
    assert should_refresh(token, TTL, current_ms=NOW + 100 * 1000) is False
    assert should_refresh(token, TTL, current_ms=NOW + (TTL // 2 + 1) * 1000) is True


# ---- giới hạn thử sai ----


class _Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_throttle_blocks_after_the_limit_and_frees_after_the_window() -> None:
    clock = _Clock()
    throttle = LoginThrottle(3, 900, clock=clock)
    for _ in range(2):
        throttle.record_failure("a@x|1.1.1.1")
    assert throttle.retry_after("a@x|1.1.1.1") == 0
    throttle.record_failure("a@x|1.1.1.1")
    assert throttle.retry_after("a@x|1.1.1.1") == 900
    clock.now += 400
    assert throttle.retry_after("a@x|1.1.1.1") == 500
    clock.now += 501
    assert throttle.retry_after("a@x|1.1.1.1") == 0


def test_throttle_is_per_key_and_reset_clears_it() -> None:
    throttle = LoginThrottle(2, 900, clock=_Clock())
    for _ in range(2):
        throttle.record_failure("victim@x|9.9.9.9")
    assert throttle.retry_after("victim@x|9.9.9.9") > 0
    assert throttle.retry_after("victim@x|1.1.1.1") == 0  # cùng email, IP khác: không bị khóa hộ
    assert throttle.retry_after("other@x|9.9.9.9") == 0
    throttle.reset("victim@x|9.9.9.9")
    assert throttle.retry_after("victim@x|9.9.9.9") == 0


def test_throttle_memory_is_bounded() -> None:
    throttle = LoginThrottle(5, 900, clock=_Clock(), max_keys=50)
    for index in range(500):
        throttle.record_failure(f"user{index}@x|1.1.1.1")
    assert len(throttle._failures) <= 50  # noqa: SLF001
