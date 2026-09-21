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
    expires_at: datetime
