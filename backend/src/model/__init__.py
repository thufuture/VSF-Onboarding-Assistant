"""Import mọi thực thể để chúng đăng ký vào Base.metadata (Alembic autogenerate và alembic check cần thấy đủ)."""

from src.model.audit_log import AuditLog
from src.model.base import Base
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.job import Job
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.user import User

__all__ = [
    "AuditLog",
    "Base",
    "Document",
    "DocumentCategory",
    "DocumentChunk",
    "DocumentSection",
    "DocumentVersion",
    "Job",
    "Team",
    "TeamMember",
    "User",
]
