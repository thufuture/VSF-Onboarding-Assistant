"""DTO phản hồi của `/api/v1/auth/*` (hợp đồng khớp `frontend/src/features/auth/dto/responseDTO/auth.response.ts`)."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel

UserRoleDTO = Literal["USER", "HR", "ADMIN"]


class SessionUserResponseDTO(BaseModel):
    id: int
    email: str
    display_name: str
    role: UserRoleDTO
    # Tên phòng ban (đội) của người dùng, nhiều đội thì nối bằng ", "; chưa thuộc đội nào thì null.
    department: str | None = None
    expires_at: datetime
