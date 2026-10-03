from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column


class LlmCall(Base):
    """Một lần gọi LLM hoặc embedding: chỉ số liệu (thời gian, token, chi phí ước tính), KHÔNG có nội dung (INV8)."""

    __tablename__ = "llm_calls"
    __table_args__ = (
        Index("ix_llm_calls_created_at", "created_at"),
        Index("ix_llm_calls_operation_created_at", "operation", "created_at"),
        Index("ix_llm_calls_job_id", "job_id"),
    )

    id: Mapped[int] = id_column()
    kind: Mapped[str] = mapped_column(String(16))  # llm | embedding
    # chat.rewrite, chat.answer, chat.embed, ingest.embed, task.proposal
    operation: Mapped[str] = mapped_column(String(48))
    provider: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    latency_ms: Mapped[float] = mapped_column(Float)
    ok: Mapped[bool] = mapped_column(Boolean)
    error: Mapped[str | None] = mapped_column(String(64))
    prompt_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    completion_tokens: Mapped[int] = mapped_column(Integer, server_default="0")
    input_count: Mapped[int] = mapped_column(Integer, server_default="0")
    cost_usd: Mapped[float] = mapped_column(Float, server_default="0")
    user_id: Mapped[int | None] = mapped_column(BigInteger)  # không khóa ngoại: xóa người dùng không mất số liệu
    request_id: Mapped[str | None] = mapped_column(String(64))
    # Việc nền sinh ra lời gọi này (không khóa ngoại: xóa job không làm mất số liệu).
    job_id: Mapped[int | None] = mapped_column(BigInteger)
    created_at: Mapped[datetime] = created_at_column()
