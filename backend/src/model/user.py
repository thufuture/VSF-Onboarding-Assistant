from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from src.model.base import Base, TimestampTZ, created_at_column, id_column, updated_at_column
from src.model.enums import UserRole, UserStatus, check_in


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        check_in("role", UserRole),
        check_in("status", UserStatus),
        # Đăng nhập không phân biệt hoa thường.
        Index("uq_users_lower_email", text("lower(email)"), unique=True),
    )

    id: Mapped[int] = id_column()
    email: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(16), server_default=UserRole.USER.value)
    status: Mapped[str] = mapped_column(String(16), server_default=UserStatus.ACTIVE.value)
    must_change_password: Mapped[bool] = mapped_column(server_default=text("false"))
    # Thu hồi phiên: mọi cookie phát hành trước mốc này bị từ chối (không có bảng `sessions`).
    session_invalid_before: Mapped[datetime | None] = mapped_column(TimestampTZ)
    last_login_at: Mapped[datetime | None] = mapped_column(TimestampTZ)
    created_by: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()
