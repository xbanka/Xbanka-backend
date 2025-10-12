from fastapi import APIRouter, status, Depends
from app.schemas.affiliate import AffiliateCodename
from app.services.auth import AuthService
from app.services.affiliate import AffiliateService
from app.db.database import get_db
from app.models import Affiliate
from sqlalchemy.orm import Session

affiliate = APIRouter(prefix='/affiliates', tags=["Affiliates"])

@affiliate.post("/codename", status_code=status.HTTP_201_CREATED, response_model=AffiliateCodename)
def set_codename(
    codename: str, 
    db: Session = Depends(get_db), 
    current_user: Affiliate = Depends(AuthService.get_current_user)
):
    
    AffiliateService.set_codename(db, current_user, codename)

    return {
        "message": "Codename set successfully",
        "codename": codename
    }


@affiliate.get("/referral", status_code=status.HTTP_200_OK)
def get_referral_link(
    db: Session = Depends(get_db), 
    current_user: Affiliate = Depends(AuthService.get_current_user)
):
    
    return AffiliateService.get_referral_code(db, current_user)


@affiliate.get("/all")
def get_all_affiliates(db: Session = Depends(get_db)):
    return AffiliateService.get_all(db)