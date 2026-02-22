from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.dashboard import DashboardDisplay
from app.services.affiliate_dashboard import DashboardService
from app.utils.auth import require_roles
from app.utils.schema import CurrentUser

dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@dashboard.get(
    "/summary", status_code=status.HTTP_200_OK, response_model=DashboardDisplay
)
def summary(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_roles("affiliate")),
):
    summary = DashboardService.get_summary(db, current_user.user)

    return summary
