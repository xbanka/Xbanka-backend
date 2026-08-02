from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import AffiliateDashboardDisplay, TransactionMetricsResponse, CustomerMetricsResponse
from app.services.dashboard import DashboardService
from app.services.internal_backend import InternalAPIService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard.get(
    "/summary", status_code=status.HTTP_200_OK, response_model=AffiliateDashboardDisplay
)
def summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    summary = DashboardService.get_affiliate_summary(db, current_user.user)

    return summary


@dashboard.get(
    "/erp/transactions/metrics", 
    status_code=status.HTTP_200_OK, 
    response_model=TransactionMetricsResponse
)
def erp_transaction_metrics(current_user: CurrentUser = Depends(require_roles("erp"))):
    metrics = InternalAPIService.get_transaction_metrics()

    return metrics


@dashboard.get(
    "/erp/customer/metrics", 
    status_code=status.HTTP_200_OK, 
    response_model=CustomerMetricsResponse
)
def erp_customer_metrics(current_user: CurrentUser = Depends(require_roles("erp"))):
    metrics = InternalAPIService.get_customer_metrics()

    return metrics