"""Giá trị hợp lệ của các cột trạng thái. Trong DB là VARCHAR + CHECK (không dùng native enum)."""

from enum import StrEnum

from sqlalchemy import CheckConstraint


class UserRole(StrEnum):
    USER = "USER"
    HR = "HR"
    ADMIN = "ADMIN"


class UserStatus(StrEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class DocumentStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class ContentKind(StrEnum):
    GENERAL = "GENERAL"
    PROCEDURE_GUIDE = "PROCEDURE_GUIDE"


class Confidentiality(StrEnum):
    # INV9: chỉ nhận tài liệu ít nhạy cảm (không có ACL tài liệu).
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"


class VersionStatus(StrEnum):
    PROCESSING = "PROCESSING"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class JobKind(StrEnum):
    INGEST_VERSION = "INGEST_VERSION"
    REINDEX = "REINDEX"
    EMBED_RECORD = "EMBED_RECORD"
    RETENTION_PURGE = "RETENTION_PURGE"
    INTEGRITY_CHECK = "INTEGRITY_CHECK"


class JobStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def check_in(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """CHECK (column IN (...)) đặt tên theo convention: ck_<bảng>_<name>."""
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or column)
