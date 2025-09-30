from app.db.database import get_db
from app.models.affiliate import Affiliate
from app.schemas.dashboard import DashboardDisplay
from app.services.auth import AuthService
from app.services.dashboard import DashboardService
from fastapi import APIRouter, status, Depends
from sqlalchemy.orm import Session

dashboard = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@dashboard.get("/summary", status_code=status.HTTP_200_OK, response_model=DashboardDisplay)
def summary(
    db: Session = Depends(get_db), 
    current_user: Affiliate = Depends(AuthService.get_current_user)
):
    summary = DashboardService.get_summary(db, current_user)
    
    return summary