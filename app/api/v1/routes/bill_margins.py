from typing import Optional

from fastapi import APIRouter, Depends, Query, status

from app.core.enums import BillProductEnum
from app.schemas.erp.bill_margins import BillMarginUpdateRequest
from app.services.internal_backend import InternalAPIService
from app.utils.auth import require_super_admin
from app.utils.schema import CurrentUser

bill_margins = APIRouter(prefix="/bills/margins", tags=["Bill margins"])


@bill_margins.get("", status_code=status.HTTP_200_OK)
def get_bill_margins(
    current_user: CurrentUser = Depends(require_super_admin),
):
    """The margin for each product that can carry one (ELECTRICITY, CABLE_TV, BETTING)."""
    return InternalAPIService.get_bill_margins()


@bill_margins.get("/history", status_code=status.HTTP_200_OK)
def get_bill_margin_history(
    product: Optional[BillProductEnum] = Query(None, description="Only this product"),
    page: int = Query(1, ge=1, description="Page number (25 entries per page)"),
    current_user: CurrentUser = Depends(require_super_admin),
):
    return InternalAPIService.get_bill_margin_history(
        product=product.value if product else None, page=page
    )


@bill_margins.put("/{product}", status_code=status.HTTP_200_OK)
def update_bill_margin(
    product: BillProductEnum,
    payload: BillMarginUpdateRequest,
    current_user: CurrentUser = Depends(require_super_admin),
):
    """Send only the fields to change. Every product starts at a FIXED ₦100
    margin that is switched on, so there is nothing to add first. There is no
    delete: switch a margin off with `isActive: false`."""
    body = payload.model_dump(mode="json", exclude_unset=True)
    body["changedBy"] = current_user.user.email
    return InternalAPIService.update_bill_margin(product.value, body)
