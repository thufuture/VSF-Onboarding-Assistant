"""Cấu hình ứng dụng, đọc từ biến môi trường (và tệp .env nếu có)."""

import secrets
from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # "../.env" là .env ở gốc repo khi chạy từ thư mục backend/; trong Docker không có tệp này thì bị bỏ qua.
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), env_file_encoding="utf-8", extra="ignore")

    app_env: Literal["development", "test", "production"] = "development"
    # Múi giờ dùng để tính "hôm nay" (as_of) cho ngày hiệu lực của tài liệu và quy trình.
    app_timezone: str = "Asia/Ho_Chi_Minh"
    log_level: str = "INFO"

    # --- Tối ưu Viga (benchmark 10/2026). Mọi cờ mặc định TẮT = hành vi cũ, bật từng cái bằng biến môi trường. ---
    # Router v2: phân biệt xã giao với ngoài phạm vi/chèn lệnh (trả OUT_OF_SCOPE thay vì INFO) và làm rõ get_day_plan.
    viga_router_v2: bool = False
    # Suy luận ẩn ở bước trả lời: "always" (như cũ), "off" (luôn tắt), "adaptive" (bật khi câu hỏi được tách thành nhiều câu con).
    answer_thinking_mode: Literal["always", "off", "adaptive"] = "always"
    # Hồ sơ truy hồi: "legacy" (như cũ: RRF k=60, hai nhánh bằng nhau, chỉ cắt theo ngân sách token) hoặc "optimized"
    # (benchmark 11/10/2026: RRF k=10, BM25 : vector = 0,1 : 1, giữ 5 section mỗi câu hỏi con). Từng tham số bên dưới, nếu đặt, ghi đè hồ sơ.
    # Cắt section (max_sections) chỉ an toàn đi cùng RRF tối ưu: với RRF mặc định, Recall tụt 98,7% xuống 77%.
    retrieval_profile: Literal["legacy", "optimized"] = "legacy"
    rrf_k: int | None = Field(default=None, ge=1)
    rrf_weight_bm25: float | None = Field(default=None, ge=0)
    rrf_weight_vector: float | None = Field(default=None, ge=0)
    # Giới hạn số section cha mỗi câu hỏi con sau RRF (0 = chỉ cắt theo ngân sách token như cũ).
    retrieval_max_sections: int | None = Field(default=None, ge=0)
    # Số chỗ (trong max_sections) dành cho các mục đứng đầu của BM25, bảo hiểm cho câu cần khớp đúng chuỗi khi trọng số BM25 thấp.
    retrieval_bm25_reserve: int | None = Field(default=None, ge=0)
    # Bỏ section có điểm RRF < tỉ lệ này * điểm section đầu (0 = tắt).
    retrieval_min_score_ratio: float = 0.0
    # Trần tổng token ngữ cảnh của MỌI câu hỏi con trong một lượt trả lời (0 = tắt).
    retrieval_total_token_cap: int = 0
    # Không đưa lại section đã có ở câu hỏi con trước vào prompt.
    retrieval_dedupe_sections: bool = False

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
    # Giữ dịch vụ embedding ấm khi đang có người dùng (Modal tắt container khi rảnh, khởi động nguội mất ~20 giây).
    embedding_keep_warm_enabled: bool = True
    embedding_keep_warm_interval_seconds: float = 45.0
    embedding_keep_warm_window_seconds: float = 600.0
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
    # Giới hạn lời gọi LLM song song (nhà cung cấp cho 11 mỗi tài khoản, vượt thì 429): tổng 9, riêng việc nền 5 để không chiếm
    # chỗ của Viga. Thử lại tối đa `llm_max_retries` lần khi 429/5xx/mất kết nối (xem infrastructure/ai/llm_gate.py).
    llm_max_concurrent: int = 9
    llm_background_max_concurrent: int = 5
    llm_max_retries: int = 2
    # LLM dự phòng (mặc định Claude Haiku qua OpenRouter): chỉ dùng khi nhà cung cấp chính lỗi hạ tầng. Tắt nếu thiếu khóa.
    llm_fallback_enabled: bool = False
    llm_fallback_base_url: str = "https://openrouter.ai/api/v1"
    llm_fallback_model: str = "anthropic/claude-haiku-5.5"
    llm_fallback_api_key: SecretStr | None = None
    llm_fallback_timeout_seconds: float = 30
    # Trần token đầu ra của nhà cung cấp dự phòng (OpenRouter giữ chỗ chi phí theo trần này; mặc định của họ rất lớn).
    llm_fallback_max_output_tokens: int = 4000
    # Việc nền (sinh task bằng AI) có dùng dự phòng không: mặc định không, vì đổi mô hình có thể đổi chất lượng task; thử lại sau là đủ.
    llm_fallback_for_background: bool = False
    llm_fallback_failure_threshold: int = 3
    llm_fallback_cooldown_seconds: float = 60

    # Tạo task bằng AI (kế hoạch tối ưu độ trễ, Ai-task/ke-hoach-toi-uu-tao-task-bang-ai.md): "fast" = tắt suy luận, trích
    # nguồn bằng số dòng, một lượt bù phủ và một lời gọi xếp thứ tự; "legacy" = cách cũ (suy luận bật, trích nguyên văn).
    task_proposal_mode: Literal["fast", "legacy"] = "fast"
    task_proposal_batch_words: int = 2500
    task_proposal_call_timeout_seconds: float = 60

    # Theo dõi từng bước gọi LLM/embedding bằng Langfuse (tùy chọn — mục 7, kế hoạch 2-C/2-D mở rộng).
    # Tắt mặc định; bật khi có khóa. Mặc định chỉ gửi số liệu (token, chi phí, độ trễ, số lượng). Nội dung câu hỏi, câu trả
    # lời và tài liệu là dữ liệu nội bộ đi ra dịch vụ ngoài: chỉ gửi khi đặt LANGFUSE_CAPTURE_CONTENT=true.
    langfuse_enabled: bool = False
    langfuse_capture_content: bool = False
    langfuse_content_max_chars: int = 4000
    langfuse_public_key: str | None = None
    langfuse_secret_key: SecretStr | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # Đơn giá để ƯỚC TÍNH chi phí (USD). Mặc định 0 = chưa biết đơn giá, số liệu chi phí khi đó hiển thị 0 chứ không
    # đoán. Điền theo bảng giá thật của nhà cung cấp (LLM: USD mỗi 1 triệu token; embedding: USD mỗi giây GPU).
    # DeepSeek `deepseek-flash` tra ngày 01/10/2026 (giá giờ cao điểm, cache miss: mức bảo thủ); xem mục 12.11a của
    # plan-portal/ingest-tai-lieu-va-tao-task-bang-ai.md. Đặt 0 nếu muốn tắt ước tính.
    llm_price_input_per_million_usd: float = 0.30
    llm_price_output_per_million_usd: float = 1.20
    # Embedding BGE-M3 do dự án tự host (máy EC2 riêng, tính tiền theo giờ thuê máy chứ không theo lời gọi) nên mặc định KHÔNG tính
    # chi phí theo lời gọi. Nếu quay lại dùng Modal (GPU L4, $0.000222/giây theo modal.com/pricing tra 05/10/2026) thì đặt
    # EMBEDDING_PRICE_PER_SECOND_USD=0.000222; thống kê chi phí trên giao diện vẫn chỉ cộng LLM.
    embedding_price_per_second_usd: float = 0.0

    # Hàng đợi việc nền (nạp/kích hoạt tài liệu, tạo task bằng AI) chạy trong tiến trình backend (mục 14).
    job_worker_enabled: bool = True
    job_max_concurrent: int = 2
    job_poll_seconds: float = 1.0
    # Job RUNNING không báo tiến độ quá lâu thì coi là worker đã chết và đưa về hàng đợi.
    job_stale_seconds: int = 300

    # LLM chia mục cho tài liệu kém cấu trúc (mục 13.2b): chỉ chạy khi luật cố định không tìm được tiêu đề, tài liệu đủ
    # dài, và chưa vượt hạn mức số lần gọi mỗi ngày. Chỉ gửi chữ của tài liệu đã có (không OCR).
    # Hội thoại Viga lưu trong PostgreSQL, tự xóa sau số ngày không hoạt động này (quyết định 8, mục 0.1).
    chat_retention_days: int = 90

    structure_llm_enabled: bool = True
    structure_llm_min_words: int = 400
    structure_llm_daily_limit: int = 30

    # Kích hoạt phiên bản chỉ tính embedding cho đoạn mới hoặc đã sửa, dùng lại vector của đoạn không đổi (cùng model).
    embedding_cache_enabled: bool = False

    # Trình soạn thảo kiểu Word (ONLYOFFICE Docs, máy chủ riêng) cho bản nháp. Tắt mặc định; cần đủ cả bốn địa chỉ/khóa bên dưới.
    # public_url: địa chỉ trình duyệt dùng để tải trình soạn thảo; internal_url: backend gọi chuyển đổi/lưu; backend_url: địa chỉ
    # backend mà máy chủ ONLYOFFICE gọi tới (lấy file, callback lưu); jwt_secret: khóa JWT dùng chung với ONLYOFFICE.
    word_editor_enabled: bool = False
    # PDF gốc -> Word giữ bố cục bằng pdf2docx (PyMuPDF: AGPL, cân nhắc pháp lý trước khi bật). Tắt thì dựng Word từ Markdown.
    pdf_to_word_enabled: bool = False
    pdf_to_word_max_pages: int = 100

    # Đọc PDF có chữ giữ cấu trúc: tiêu đề theo cỡ chữ/độ đậm, đoạn, danh sách (pdfminer, không thêm thư viện). Tắt thì dùng bộ đọc phẳng cũ.
    pdf_structure_enabled: bool = False

    # OCR cho PDF scan (OCRmyPDF + Tesseract, gói tiếng Việt). Chạy nền, tắt mặc định; cần cài công cụ trong ảnh Docker.
    ocr_enabled: bool = False
    ocr_languages: str = "vie+eng"
    ocr_max_pages: int = 60
    ocr_jobs: int = 1
    ocr_timeout_seconds: int = 1800
    onlyoffice_public_url: str = ""
    onlyoffice_internal_url: str = ""
    onlyoffice_backend_url: str = ""
    onlyoffice_jwt_secret: SecretStr | None = None

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


@dataclass(frozen=True)
class RetrievalTuning:
    rrf_k: int
    weight_bm25: float
    weight_vector: float
    max_sections: int
    bm25_reserve: int = 0


_PROFILES: dict[str, RetrievalTuning] = {
    "legacy": RetrievalTuning(rrf_k=60, weight_bm25=1.0, weight_vector=1.0, max_sections=0),
    "optimized": RetrievalTuning(rrf_k=10, weight_bm25=0.1, weight_vector=1.0, max_sections=5),
}


def resolve_retrieval_tuning(settings: Settings) -> RetrievalTuning:
    """Tham số truy hồi hiệu lực: hồ sơ làm nền, từng biến môi trường đã đặt thì ghi đè."""
    base = _PROFILES[settings.retrieval_profile]
    return RetrievalTuning(
        rrf_k=base.rrf_k if settings.rrf_k is None else settings.rrf_k,
        weight_bm25=base.weight_bm25 if settings.rrf_weight_bm25 is None else settings.rrf_weight_bm25,
        weight_vector=base.weight_vector if settings.rrf_weight_vector is None else settings.rrf_weight_vector,
        max_sections=base.max_sections if settings.retrieval_max_sections is None else settings.retrieval_max_sections,
        bm25_reserve=base.bm25_reserve if settings.retrieval_bm25_reserve is None else settings.retrieval_bm25_reserve,
    )


_WEAK_MARKERS = ("change", "secret", "password", "example", "default", "dev")


def _is_weak_secret(value: str) -> bool:
    lowered = value.lower()
    return len(value) < 32 or any(marker in lowered for marker in _WEAK_MARKERS) or len(set(value)) < 8


@lru_cache
def get_settings() -> Settings:
    return Settings()
