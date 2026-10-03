"""Import mọi thực thể để chúng đăng ký vào Base.metadata (Alembic autogenerate và alembic check cần thấy đủ)."""

from src.model.approved_link import ApprovedLink
from src.model.audit_log import AuditLog
from src.model.base import Base
from src.model.chat_conversation import ChatConversation
from src.model.chat_message import ChatMessage
from src.model.contact_channel import ContactChannel
from src.model.content_gap import ContentGap
from src.model.document import Document
from src.model.document_category import DocumentCategory
from src.model.document_chunk import DocumentChunk
from src.model.document_section import DocumentSection
from src.model.document_version import DocumentVersion
from src.model.employee_journey import EmployeeJourney
from src.model.employee_task import EmployeeTask
from src.model.job import Job
from src.model.journey_stage import JourneyStage
from src.model.journey_template import JourneyTemplate
from src.model.llm_call import LlmCall
from src.model.task_dependency import TaskDependency
from src.model.task_source_mapping import TaskSourceMapping
from src.model.task_template import TaskTemplate
from src.model.team import Team
from src.model.team_member import TeamMember
from src.model.ticket import Ticket
from src.model.ticket_message import TicketMessage
from src.model.user import User
from src.model.viga_feedback import VigaFeedback

__all__ = [
    "ApprovedLink",
    "AuditLog",
    "Base",
    "ChatConversation",
    "ChatMessage",
    "ContactChannel",
    "ContentGap",
    "Document",
    "DocumentCategory",
    "DocumentChunk",
    "DocumentSection",
    "DocumentVersion",
    "EmployeeJourney",
    "EmployeeTask",
    "Job",
    "JourneyStage",
    "JourneyTemplate",
    "LlmCall",
    "TaskDependency",
    "TaskSourceMapping",
    "TaskTemplate",
    "Team",
    "TeamMember",
    "Ticket",
    "TicketMessage",
    "User",
    "VigaFeedback",
]
