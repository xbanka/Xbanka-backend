from pydantic import BaseModel, ConfigDict

class TokenData(BaseModel):
    id: str

class LoginBase(BaseModel):
    email: str
    password: str

class UserAuth(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    email: str
    phone_no: str
    bank: str

class LoginResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    token_type: str

class RegisterBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone_no: str
    bank: str
    account_no: str
    password: str

class RegisterResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    user: UserAuth