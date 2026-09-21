"""DTO phản hồi của `GET /api/v1/health` và `GET /api/v1/ready`."""

from typing import Any, Literal

from pydantic import BaseModel


class HealthResponseDTO(BaseModel):
    status: Literal["ok"]


class ReadyResponseDTO(BaseModel):
    """Báo cáo sẵn sàng: `checks` gồm kết quả từng mục (database, migration, extensions)."""

    status: Literal["ready", "not_ready"]
    checks: dict[str, Any]
