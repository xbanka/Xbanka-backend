from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.core.enums import BillMarginTypeEnum


def _check_percentage(margin_type, margin_value) -> None:
    if (
        margin_type == BillMarginTypeEnum.PERCENTAGE
        and margin_value is not None
        and margin_value > 100
    ):
        raise ValueError("A percentage margin cannot exceed 100")


class BillMarginUpdateRequest(BaseModel):
    """Who is making the change (`changedBy`) is taken from the signed-in
    staff member, not from the request body."""

    marginType: Optional[BillMarginTypeEnum] = None
    marginValue: Optional[float] = Field(default=None, ge=0)
    isActive: Optional[bool] = None
    reason: str = Field(min_length=3)

    @model_validator(mode="after")
    def _validate(self):
        if not self.model_fields_set - {"reason"}:
            raise ValueError("Provide at least one field to update")
        _check_percentage(self.marginType, self.marginValue)
        return self
