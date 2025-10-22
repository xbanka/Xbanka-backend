from pydantic import BaseModel, ConfigDict
from uuid import UUID

class CustomerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    first_name: str
    first_name: str
    email: str
    phone_no: str
    commission: float