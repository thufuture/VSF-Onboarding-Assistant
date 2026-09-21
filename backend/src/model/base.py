"""Lớp cơ sở cho mô hình ORM và các kiểu dùng chung (database-design mục 1 và 5)."""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Identity, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Tên ràng buộc ổn định để Alembic sinh migration và so sánh (alembic check) không lệch giữa các máy.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
    "ex": "ex_%(table_name)s_%(constraint_name)s",
}

# Thời gian luôn có múi giờ (UTC trong DB); ngày hiệu lực là DATE theo giờ Việt Nam (xem config.app_timezone).
TimestampTZ = DateTime(timezone=True)

# BGE-M3 cho vector 1024 chiều.
EMBEDDING_DIMENSION = 1024
Embedding = Vector(EMBEDDING_DIMENSION)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def id_column() -> Mapped[int]:
    """Khóa chính BIGINT GENERATED ALWAYS AS IDENTITY."""
    return mapped_column(BigInteger, Identity(always=True), primary_key=True)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(TimestampTZ, server_default=func.now())


def updated_at_column() -> Mapped[datetime]:
    """Cập nhật ở tầng ứng dụng (onupdate), theo quy ước của database-design."""
    return mapped_column(TimestampTZ, server_default=func.now(), onupdate=func.now())
