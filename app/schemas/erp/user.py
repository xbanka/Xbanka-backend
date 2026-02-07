from typing import List
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator, ValidationInfo
from fastapi import HTTPException
from uuid import UUID
from pydantic import EmailStr
from datetime import datetime


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    

class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    permission_links: List[str] = Field(..., alias="allowed_permissions")

    @field_validator("permission_links", mode="before")
    def _filter_out_forbidden(cls, v):
        allowed_links = list(filter(lambda x: x.is_allowed, v))
        return [
            getattr(getattr(link, "permission", None), "name", None)
            for link in allowed_links
        ]

class ERPMeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    email: EmailStr
    role: RoleResponse
    created_at: datetime

class AllStaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    staff: List[ERPMeResponse]
    count: int

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str


class LoginBase(BaseModel):
    email: str
    password: str


class RegisterBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str
    confirm_password: str

    @field_validator("confirm_password", mode="after")
    def passwords_match(cls, v, values: ValidationInfo):
        password = values.data.get("password")
        if password and v != password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        return v
    

class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str


class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    user: UserBase


class LogoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password", mode="after")
    def passwords_match(cls, v, values: ValidationInfo):
        password = values.data.get("new_password")
        if password and v != password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        return v
    

class VerifyResponse(BaseModel):
    """ Schema for successful verification response """
    model_config = ConfigDict(from_attributes=True)

    message: str


class InviteStaffRequest(BaseModel):
    email: str
    role: str
    permissions: List[str]


class UpdateStaffRequest(BaseModel):
    first_name: str
    last_name: str
    email: str


class UpdatePermissionsRequest(BaseModel):
    role: str
    permissions: List[str]
