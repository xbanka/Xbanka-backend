from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import AffiliateDashboardDisplay, ERPDashboardDisplay
from app.services.dashboard import DashboardService
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


@dashboard.get("/erp/stats", status_code=status.HTTP_200_OK, response_model=ERPDashboardDisplay)
def erp_stats(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("super")),
):
    stats = DashboardService.get_erp_stats(db)

    return stats