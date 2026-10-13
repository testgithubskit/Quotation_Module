from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel
from app.schemas.text_rules import reject_person_name_spaces


class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    code: str = Field(..., min_length=2, max_length=50)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tax_number: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    custom_data: dict = Field(default_factory=dict)


class OrganizationUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    tax_number: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None
    custom_data: Optional[dict] = None

    @field_validator("name")
    @classmethod
    def name_spacing(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return reject_person_name_spaces(value, "Organization name")


class OrganizationResponse(ORMModel):
    id: UUID
    name: str
    code: str
    email: Optional[str]
    phone: Optional[str]
    website: Optional[str]
    tax_number: Optional[str]
    address: Optional[str]
    notes: Optional[str]
    is_active: bool
    custom_data: dict
    created_at: datetime
    updated_at: datetime
