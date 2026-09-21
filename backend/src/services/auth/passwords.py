"""Băm và kiểm mật khẩu bằng scrypt (chép từ Ralion): định dạng `scrypt$<salt hex>$<digest hex>`."""

import hashlib
import hmac
import os
from functools import cache

_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P)
    return f"scrypt${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str | None) -> bool:
    """Đúng khi khớp; chuỗi lưu rỗng hoặc sai định dạng thì trả False (không ném lỗi)."""
    if not encoded:
        return False
    try:
        scheme, salt_hex, digest_hex = encoded.split("$", 2)
        if scheme != "scrypt":
            return False
        expected = hashlib.scrypt(
            password.encode(), salt=bytes.fromhex(salt_hex), n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P
        )
        return hmac.compare_digest(expected.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


@cache
def dummy_hash() -> str:
    """Băm giả để đăng nhập với email không tồn tại vẫn tốn thời gian tương đương (chống dò email qua thời gian)."""
    return hash_password("khong-ai-dung-mat-khau-nay", salt=b"\x00" * 16)
