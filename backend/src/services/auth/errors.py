from collections.abc import Mapping


class AuthError(Exception):
    """Lỗi xác thực/phân quyền; app chuyển thành `{code, message_key, detail}` (system design mục 9)."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message_key: str,
        *,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status_code = status_code
        self.code = code
        self.message_key = message_key
        self.headers = dict(headers) if headers else None
