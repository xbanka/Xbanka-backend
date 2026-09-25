from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import HTTPException
from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    ValidationInfo,
    computed_field,
    field_validator,
    model_validator,
)

from app.schemas.erp.audit import PendingRoleChangeSummary, RoleChangeDetail
from app.utils.s3_utils import get_image_url
from app.utils.settings import settings
from app.utils.validators import normalize_phone


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    name: str
    # Resolved by Role.allowed_permissions, which special-cases Super Admin to
    # the full permissions table rather than its own role_permissions rows.
    allowed_permissions: List[str]


class StaffBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    staff_code: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None
    avatar_url: Optional[str] = None
    role: RoleResponse
    created_at: datetime
    verified: bool


class ERPMeResponse(StaffBase):
    pending_role_change: Optional[PendingRoleChangeSummary] = None

    @computed_field
    @property
    def avatar_signed_url(self) -> Optional[str]:
        """Short-lived link the browser can load the avatar from. avatar_url is
        only the S3 key, and the bucket is private."""
        if not self.avatar_url or not settings.S3_BUCKET_AVATARS:
            return None
        return get_image_url(self.avatar_url, settings.S3_BUCKET_AVATARS)


class UpdateERPRequest(BaseModel):
    """A staff member's edits to their own profile. Omitted fields are left
    as they are; phone can be sent as null or "" to clear it."""

    model_config = ConfigDict(extra="forbid")

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None

    @field_validator("first_name", "last_name", mode="before")
    @classmethod
    def _clean_name(cls, v, info: ValidationInfo):
        # field_name is typed Optional; it's always set here, since this
        # validator is only attached to first_name and last_name.
        label = (info.field_name or "name").replace("_", " ").capitalize()
        if v is None or (isinstance(v, str) and not v.strip()):
            raise HTTPException(status_code=400, detail=f"{label} cannot be empty.")
        if not isinstance(v, str):
            raise HTTPException(status_code=400, detail=f"{label} must be text.")
        v = v.strip()
        if len(v) > 100:  # matches the erp_users column length
            raise HTTPException(
                status_code=400, detail=f"{label} must be at most 100 characters."
            )
        return v

    @field_validator("phone", mode="before")
    @classmethod
    def _normalize_phone(cls, v):
        if v is None or (isinstance(v, str) and not v.strip()):
            return None
        normalized = normalize_phone(v) if isinstance(v, str) else None
        if normalized is None:
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number. Use a Nigerian number (e.g. 08031234567) "
                "or include the country code (e.g. +447911123456).",
            )
        return normalized

    @model_validator(mode="after")
    def _require_a_field(self):
        if not self.model_fields_set:
            raise HTTPException(
                status_code=400,
                detail="Provide at least one of first_name, last_name or phone.",
            )
        return self


class StaffListItem(StaffBase):
    # Set only while a role change awaits the staff member's confirmation;
    # null when there's none or once it has been confirmed.
    role_change: Optional[RoleChangeDetail] = None


class AllStaffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    staff: List[StaffListItem]
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


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

    @field_validator("confirm_password", mode="after")
    def passwords_match(cls, v, values: ValidationInfo):
        password = values.data.get("new_password")
        if password and v != password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        return v


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
    """Schema for successful verification response"""

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
    role: Optional[str] = None
    permissions: Optional[List[str]] = None
    reason: Optional[str] = None

    @model_validator(mode="after")
    def _require_role_or_permissions(self):
        if self.role is None and self.permissions is None:
            raise ValueError("At least one of 'role' or 'permissions' must be provided.")
        return self


class UpdatePermissionsResponse(BaseModel):
    message: str
    staff: ERPMeResponse
