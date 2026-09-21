"""Cấu hình ứng dụng, đọc từ biến môi trường (và tệp .env nếu có)."""

from functools import lru_cache
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import field_validator
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

    @field_validator("app_timezone")
    @classmethod
    def _timezone_must_exist(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as exc:
            # ZoneInfoNotFoundError là KeyError, không phải ValueError: phải đổi thì pydantic mới báo lỗi xác thực.
            raise ValueError(f"múi giờ không tồn tại: {value}") from exc
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
