from fastapi import APIRouter, Depends
from app.utils.auth import require_role
from app.services.erp_user import ERPService
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth import AuthService

erp = APIRouter(prefix="/erp", tags=["ERP"])

@erp.get("/")
def get_index(user = Depends(require_role("erp"))):
    return {
        "message": "hey"
}

@erp.get("/notifications")
def get_notifications(db: Session = Depends(get_db), current_user = Depends(AuthService.get_current_user)):
    return ERPService.get_notifications(db, current_user)