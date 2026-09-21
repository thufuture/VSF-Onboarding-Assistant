from datetime import datetime

from sqlalchemy import Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, created_at_column, id_column, updated_at_column


class DocumentCategory(Base):
    """Mục tài liệu là bảng, không phải enum: HR thêm/sửa/ẩn mà không cần sửa mã."""

    __tablename__ = "document_categories"

    id: Mapped[int] = id_column()
    slug: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(120))
    # Điểm neo miền khi định tuyến câu hỏi.
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
