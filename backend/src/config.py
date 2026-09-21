"""Cấu hình ứng dụng, đọc từ biến môi trường (và tệp .env nếu có)."""

import secrets
from functools import lru_cache
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "../.env" là .env ở gốc repo khi chạy từ thư mục backend/; trong Docker không có tệp này thì bị bỏ qua.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    # Múi giờ dùng để tính "hôm nay" (as_of) cho ngày hiệu lực của tài liệu và quy trình.
    app_timezone: str = "Asia/Ho_Chi_Minh"
    log_level: str = "INFO"

    # Mặc định trỏ tới cổng host của docker-compose (POSTGRES_HOST_PORT); mật khẩu vsf/vsf chỉ là của môi trường dev.
    database_url: str = "postgresql+asyncpg://vsf:vsf@localhost:5434/vsf"

    # Khóa ký cookie phiên. Bắt buộc và phải mạnh ở production; ngoài production để trống thì mỗi lần khởi động
    # tự sinh khóa ngẫu nhiên (phiên mất khi khởi động lại, đủ cho dev và test).
    session_secret: SecretStr | None = None
    session_ttl_seconds: int = 30 * 60
    # Giới hạn thử sai theo (email, IP): quá ngưỡng trong cửa sổ thì bị chặn tạm. Đếm trong tiến trình (một worker).
    login_max_failures: int = 5
    login_window_seconds: int = 15 * 60

    @field_validator("app_timezone")
    @classmethod
    def _timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            # ZoneInfoNotFoundError là KeyError, không phải ValueError: phải đổi thì pydantic mới báo lỗi xác thực.
            raise ValueError(f"múi giờ không tồn tại: {value}") from exc
        return value

    @model_validator(mode="after")
    def _session_secret_rules(self) -> Self:
        if self.session_secret is None:
            if self.app_env == "production":
                raise ValueError("SESSION_SECRET là bắt buộc ở production")
            self.session_secret = SecretStr(secrets.token_hex(32))
        elif self.app_env == "production" and _is_weak_secret(self.session_secret.get_secret_value()):
            raise ValueError("SESSION_SECRET quá yếu: cần ít nhất 32 ký tự và không phải giá trị mẫu")
        return self


_WEAK_MARKERS = ("change", "secret", "password", "example", "default", "dev")


def _is_weak_secret(value: str) -> bool:
    lowered = value.lower()
    return len(value) < 32 or any(marker in lowered for marker in _WEAK_MARKERS) or len(set(value)) < 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
