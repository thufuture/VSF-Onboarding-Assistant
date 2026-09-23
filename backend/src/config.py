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
    # Giới hạn số câu hỏi /chat/ask theo user_id (mục 4.4, 2-e-prompt-guardrail-rerank/03): endpoint tốn tiền
    # thật (LLM + embedding) mỗi lần gọi, cần chặn lạm dụng/vòng lặp lỗi — nhưng vẫn đủ rộng để một người
    # test tay hỏi liên tục không bị chặn (100 câu/5 phút ~ nhanh hơn nhiều so với tốc độ gõ tay thật).
    chat_max_questions: int = 100
    chat_window_seconds: int = 5 * 60

    # Embedding BGE-M3 khi nạp tài liệu (2-B): "modal-bge-m3" gọi dịch vụ thật, "fake" dùng vector giả
    # tất định (mặc định, an toàn cho dev/CI — không gọi mạng nếu chưa cấu hình).
    embedding_provider: Literal["modal-bge-m3", "fake"] = "fake"
    embedding_endpoint: str | None = None
    embedding_api_key: SecretStr | None = None
    # Timeout/retry riêng cho lúc nạp tài liệu (khác với lúc chat, chưa cần ở Phase 2).
    ingestion_embedding_connect_timeout_seconds: float = 5
    ingestion_embedding_read_timeout_seconds: float = 120
    ingestion_embedding_max_attempts: int = 4
    ingestion_embedding_backoff_initial_seconds: float = 1
    ingestion_embedding_backoff_multiplier: float = 3
    ingestion_embedding_backoff_max_seconds: float = 9

    # Lưu file tài liệu gốc (2-B): "local" (mặc định, an toàn cho dev/CI, không cần tài khoản ngoài)
    # ghi vào storage_path trên đĩa; "cloudinary" đẩy lên Cloudinary, DB chỉ lưu URL (storage_key).
    storage_provider: Literal["local", "cloudinary"] = "local"
    storage_path: str = "./storage"
    cloudinary_cloud_name: str | None = None
    cloudinary_api_key: str | None = None
    cloudinary_api_secret: SecretStr | None = None

    # LLM (2-D): DeepSeek qua giao diện tương thích OpenAI. Không hard-code tên model.
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-flash"
    llm_api_key: SecretStr | None = None

    # Theo dõi từng bước gọi LLM/embedding bằng Langfuse (tùy chọn — mục 7, kế hoạch 2-C/2-D mở rộng).
    # Tắt mặc định; bật khi có khóa. Chỉ metadata được gửi đi, không gửi nội dung câu hỏi/câu trả lời thật.
    langfuse_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

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
