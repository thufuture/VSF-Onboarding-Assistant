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
    DRAFT = "DRAFT"
    PROCESSING = "PROCESSING"
    PENDING_REVIEW = "PENDING_REVIEW"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"
    FAILED = "FAILED"


class VersionSource(StrEnum):
    UPLOAD = "UPLOAD"
    EDITED = "EDITED"


class JobKind(StrEnum):
    INGEST_VERSION = "INGEST_VERSION"
    ACTIVATE_VERSION = "ACTIVATE_VERSION"
    AI_TASK_PROPOSAL = "AI_TASK_PROPOSAL"
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


class StageVersionStatus(StrEnum):
    """Phiên bản của một ngày: DRAFT sửa được, APPLIED là bản đang áp dụng (tối đa một), ARCHIVED là bản từng áp dụng."""

    DRAFT = "DRAFT"
    APPLIED = "APPLIED"
    ARCHIVED = "ARCHIVED"


class ChangeKind(StrEnum):
    """Loại thay đổi của một việc khi HR áp dụng bản mới (so theo origin_key)."""

    MODIFIED = "MODIFIED"
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    PREREQUISITES = "PREREQUISITES"


class ChangeStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    DISMISSED = "DISMISSED"
    SUPERSEDED = "SUPERSEDED"


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


class FeedbackRating(StrEnum):
    UP = "UP"
    DOWN = "DOWN"


class FeedbackReason(StrEnum):
    """Lý do chọn nhanh khi bấm 👎 (không bắt buộc)."""

    WRONG = "WRONG"  # sai thông tin
    MISSING = "MISSING"  # thiếu thông tin
    UNCLEAR = "UNCLEAR"  # khó hiểu / lộn xộn
    OFF_TOPIC = "OFF_TOPIC"  # không đúng ý tôi hỏi


class GapKind(StrEnum):
    NO_BASIS = "NO_BASIS"  # tài liệu không có căn cứ cho cả câu hỏi
    PARTIAL = "PARTIAL"  # trả lời được một phần, phần còn lại tài liệu chưa quy định


class ChatRole(StrEnum):
    USER = "USER"
    ASSISTANT = "ASSISTANT"


class TicketSource(StrEnum):
    MANUAL = "MANUAL"
    VIGA = "VIGA"


class TicketStatus(StrEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


def check_in(column: str, enum: type[StrEnum], name: str | None = None) -> CheckConstraint:
    """CHECK (column IN (...)) đặt tên theo convention: ck_<bảng>_<name>."""
    values = ", ".join(f"'{member.value}'" for member in enum)
    return CheckConstraint(f"{column} IN ({values})", name=name or column)
