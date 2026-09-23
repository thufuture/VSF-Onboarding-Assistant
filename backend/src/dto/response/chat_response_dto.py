"""DTO phản hồi của `POST /api/v1/chat/ask` — `claims[]`, mỗi ý một claim độc lập (mục 6, kế hoạch
2-C/2-D mở rộng)."""

from typing import Literal

from pydantic import BaseModel


class SourceResponseDTO(BaseModel):
    document_title: str
    version_label: str
    section_heading: str | None
    # `document_versions.storage_key`: URL mở được (Cloudinary) khi nạp bằng storage_provider=cloudinary,
    # hoặc đường dẫn tương đối cục bộ (storage_provider=local, dev/CI — không mở được) khi không phải URL
    # tuyệt đối. FE chỉ hiện thành link khi bắt đầu bằng "http".
    document_url: str
    # Gọi `GET /api/v1/chat/documents/{version_id}` để lấy toàn bộ nội dung, cuộn tới đúng section_heading.
    version_id: int


class ClaimResponseDTO(BaseModel):
    question: str
    response_type: Literal["ANSWER", "NO_BASIS"]
    reason_code: str | None = None
    text: str | None = None
    quote: str | None = None
    source: SourceResponseDTO | None = None


class ChatAskResponseDTO(BaseModel):
    claims: list[ClaimResponseDTO]
