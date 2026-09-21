"""DTO yêu cầu của `/api/v1/auth/*` (hợp đồng khớp `frontend/src/features/auth/dto/requestDTO/auth.request.ts`)."""

from pydantic import BaseModel, Field


class LoginRequestDTO(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=1024)
