from typing import Literal

from pydantic import BaseModel, Field


class CreateUserRequestDTO(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["USER", "HR", "ADMIN"]
    team_id: int | None = None


class UpdateUserRequestDTO(BaseModel):
    display_name: str = Field(min_length=1, max_length=120)
    email: str = Field(min_length=3, max_length=255, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    role: Literal["USER", "HR", "ADMIN"]


class SetUserStatusRequestDTO(BaseModel):
    status: Literal["ACTIVE", "INACTIVE"]


class CreateTeamRequestDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    code: str = Field(min_length=2, max_length=32, pattern=r"^[A-Z0-9_]+$")
    hr_user_id: int | None = None
    copy_shared_template: bool = True


class UpdateTeamRequestDTO(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    hr_user_id: int | None = None


class SetTeamStatusRequestDTO(BaseModel):
    is_active: bool


class CreateMembershipRequestDTO(BaseModel):
    team_id: int
    user_id: int
