from uuid import UUID
from fastapi import APIRouter, Depends
from app.utils.auth import require_role
from app.services.erp_user import ERPService
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.services.auth import AuthService
from app.schemas.erp.notifications import NotificationReadResponse, NotificationsResponse 
from typing import List

erp = APIRouter(prefix="/erp", tags=["ERP"])

@erp.get("/")
def get_index(user = Depends(require_role("erp"))):
    return {
        "message": "hey"
}

@erp.get("/notifications", response_model=List[NotificationsResponse])
def get_notifications(db: Session = Depends(get_db), current_user = Depends(AuthService.get_current_user)):
    return ERPService.get_notifications(db, current_user)


@erp.patch("/notifications/{id}/mark-as-read", response_model=NotificationReadResponse)
def mark_as_read(id: UUID, db: Session = Depends(get_db), current_user = Depends(require_role("erp"))):
    notif = ERPService.mark_notification_as_read(db, id, current_user)
    return notif