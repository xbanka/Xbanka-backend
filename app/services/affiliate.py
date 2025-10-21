from app.core.base.services import Service
from app.models.affiliate import Affiliate
from app.models.transactions import Transaction
from app.models.customer import Customer

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


class AffiliateService(Service):
    @staticmethod
    def set_codename(db: Session, affiliate: Affiliate, codename: str) -> Affiliate:
        # check if codename already exists
        existing = db.query(Affiliate).filter_by(custom_refcode=codename).first()
        if existing and existing.id == affiliate.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codename already in use"
            )
        
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Codename already taken"
            )

        # set codename
        affiliate.custom_refcode = codename
        db.commit()
        db.refresh(affiliate)

        return affiliate
    
    @staticmethod
    def get_referral_code(db: Session, current_user: Affiliate):
        affiliate: Affiliate | None = db.query(Affiliate).get(current_user.id)
        if not affiliate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Affiliate not found"
            )
        return affiliate.ref_code
    

    @staticmethod
    def get_all(db: Session):
        all_affiliates = db.query(Affiliate).all()
        return all_affiliates
    

    @staticmethod
    def get_commissions(db: Session, affiliate_id):
        stmt = (
            select(Transaction)
            .options(selectinload(Transaction.customer))
            .join(Customer)
            .filter(Customer.affiliate_id == affiliate_id)
        )

        commissions = db.execute(stmt).scalars().all()
        return commissions