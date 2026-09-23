"""DTO phản hồi của `GET /api/v1/chat/documents/{version_id}` — nội dung Markdown đã parse của tài liệu,
dùng để FE hiện trong modal và cuộn tới đúng section đã trích dẫn (thay vì tải file gốc)."""

from pydantic import BaseModel


class DocumentContentResponseDTO(BaseModel):
    document_title: str
    version_label: str
    markdown: str
