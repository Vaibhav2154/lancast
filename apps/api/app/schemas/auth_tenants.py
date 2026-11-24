from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    full_name: str
    is_platform_admin: bool


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tenant_id: UUID
    role: str


class MeOut(BaseModel):
    user: UserOut
    memberships: list[MembershipOut]


class TenantCreate(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,63}$")
    name: str = Field(min_length=1, max_length=200)


class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    slug: str
    name: str
    is_active: bool


class MemberCreate(BaseModel):
    email: EmailStr
    role: Literal["tenant_admin", "organizer", "candidate"]
    full_name: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=10, max_length=128)


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str
