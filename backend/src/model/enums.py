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


class TaskGroup(StrEnum):
    """Nhóm task hiển thị bằng màu mốc trên roadmap (v15: Hồ sơ / Đào tạo / Thiết bị / Văn phòng)."""

    PROFILE = "PROFILE"
    TRAINING = "TRAINING"
    DEVICE = "DEVICE"
    OFFICE = "OFFICE"


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


class JourneyTemplateStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class EmployeeTaskStatus(StrEnum):
    """Portal — plan-portal/P0A/P0A.md D1/D4: bỏ NOT_APPLICABLE (không lọc applies_when) và
    WAITING_APPROVAL (không còn ai duyệt task, nhân viên tự bấm hoàn thành)."""

    LOCKED = "LOCKED"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_EXTERNAL = "WAITING_EXTERNAL"
    BLOCKED = "BLOCKED"
    DONE = "DONE"
    SKIPPED = "SKIPPED"


class ReferenceStatus(StrEnum):
    """Trạng thái duyệt cho contact_channels/approved_links (ke-hoach-portal-onboarding.md §4.3)."""

    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


def check_in(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """CHECK (column IN (...)) đặt tên theo convention: ck_<bảng>_<name>."""
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or column)
