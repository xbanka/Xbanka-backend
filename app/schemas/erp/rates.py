from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import Optional
from uuid import UUID

class RatesSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: Optional[str] = Field(None, description="The currency code (e.g., USD, EUR)")
    name: Optional[str] = Field(None, description="The name of the currency (e.g., US Dollar, Euro)")
    isActive: Optional[bool] = Field(None, description="Whether the currency is active or not")
    buyFeeType: Optional[str] = Field(None, description="The type of buy fee (e.g., percentage, fixed)")
    buyFeeValue: Optional[float] = Field(None, description="The value of the buy fee")
    sellFeeType: Optional[str] = Field(None, description="The type of sell fee (e.g., percentage, fixed)")
    sellFeeValue: Optional[float] = Field(None, description="The value of the sell fee")
    segmentId: Optional[UUID] = Field(None, description="The id of segment crypto belongs to")


class SegmentSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="The id of segment")
    name: str = Field(..., description="The name of the segment")
    isActive: bool = Field(..., description="Whether the segment is active or not")
    buyFeeType: str = Field(..., description="The type of buy fee (e.g., percentage, fixed)")
    buySpread: float = Field(..., description="The value of the buy spread")
    sellFeeType: str = Field(..., description="The type of sell fee (e.g., percentage, fixed)")
    sellSpread: float = Field(..., description="The value of the sell spread")