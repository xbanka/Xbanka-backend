from pydantic import BaseModel, ConfigDict

class DashboardDisplay(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    total_customers: int
    signed_up: int
    converted: int
    total_commission: float