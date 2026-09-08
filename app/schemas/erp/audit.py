from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.core.enums import LoginStatusEnum, RoleChangeStatusEnum


class StaffSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    last_name: str
    staff_code: str


class RoleChangeDetail(BaseModel):
    previous_role: str
    new_role: str


class RoleChangeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    changed_by: str
    staff: StaffSummary
    role_change: RoleChangeDetail
    reason: Optional[str]
    status: RoleChangeStatusEnum


class LoginLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    staff: Optional[StaffSummary]
    ip_address: Optional[str]
    failure_reason: Optional[str]
    status: LoginStatusEnum


class PendingRoleChangeSummary(BaseModel):
    id: UUID
    new_role: str
    reason: Optional[str]
    requested_by: str
    created_at: datetime


class RoleChangeProposedResponse(BaseModel):
    message: str
    role_change_id: UUID
    status: RoleChangeStatusEnum
