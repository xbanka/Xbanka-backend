from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator, ValidationInfo
from fastapi import HTTPException
from uuid import UUID

class TokenData(BaseModel):
    id: UUID

class LoginBase(BaseModel):
    email: str
    password: str

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
    bank: str
    verified: bool

class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str

class RegisterBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    username: Optional[str] = None
    phone_no: str
    bank: str
    account_no: str
    password: str
    confirm_password: str

    @field_validator("confirm_password", mode="after")
    def passwords_match(cls, v, values: ValidationInfo):
        password = values.data.get("password")
        if password and v != password:
            raise HTTPException(status_code=400, detail="Passwords do not match")
        return v
    
class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    user: UserBase

class LogoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    success: bool
    message: str


class VerifyResponse(BaseModel):
    """ Schema for successful verification response """
    model_config = ConfigDict(from_attributes=True)

    message: str

class AccountVerificationRequest(BaseModel):
    first_name: str
    last_name: str
    account_number: str
    bank_name: str


class AccountVerificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    status: str
    message: str
    verified_name: str
    bank: str

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