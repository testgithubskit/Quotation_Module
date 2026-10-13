from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.text_rules import reject_password_spaces, reject_person_name_spaces


class SignupRequest(BaseModel):
    organization_name: str = Field(..., min_length=2, max_length=255)
    organization_code: str = Field(..., min_length=2, max_length=50)
    address: Optional[str] = Field(None, max_length=1000)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)

    @field_validator("password")
    @classmethod
    def password_has_no_spaces(cls, value: str) -> str:
        return reject_password_spaces(value)

    @field_validator("organization_name")
    @classmethod
    def organization_name_spacing(cls, value: str) -> str:
        return reject_person_name_spaces(value, "Organization name")

    @field_validator("organization_code")
    @classmethod
    def organization_code_spacing(cls, value: str) -> str:
        return reject_person_name_spaces(value, "Organization code")

    @field_validator("full_name")
    @classmethod
    def full_name_spacing(cls, value: str) -> str:
        return reject_person_name_spaces(value)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)

    @field_validator("password")
    @classmethod
    def password_has_no_spaces(cls, value: str) -> str:
        return reject_password_spaces(value)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def new_password_has_no_spaces(cls, value: str) -> str:
        return reject_password_spaces(value)


class CurrentUserResponse(ORMModel):
    id: UUID
    organization_id: UUID
    organization_name: Optional[str] = None
    organization_address: Optional[str] = None
    role_id: UUID
    role_name: str
    email: EmailStr
    full_name: str
    phone: Optional[str]
    is_active: bool
    permissions: list[str]
    created_at: datetime
