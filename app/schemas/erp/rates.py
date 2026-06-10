from pydantic import BaseModel, Field
from pydantic import ConfigDict

class PostRatesRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str = Field(..., description="The currency code (e.g., USD, EUR)")
    name: str = Field(..., description="The name of the currency (e.g., US Dollar, Euro)")
    isActive: bool = Field(..., description="Whether the currency is active or not")
    buyFeeType: str = Field(..., description="The type of buy fee (e.g., percentage, fixed)")
    buyFeeValue: float = Field(..., description="The value of the buy fee")
    sellFeeType: str = Field(..., description="The type of sell fee (e.g., percentage, fixed)")
    sellFeeValue: float = Field(..., description="The value of the sell fee")
