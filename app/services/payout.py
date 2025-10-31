from app.core.base.services import Service
from app.models.payouts import Payout
from app.schemas.payout import PayoutBase

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

class PayoutService(Service):
    @staticmethod
    def create_new(db: Session, obj_in: PayoutBase, affiliate_id) -> Payout:

        existing_ref = db.execute(
            select(Payout).where(Payout.payment_ref == obj_in.payment_ref)
        ).scalar_one_or_none()
        
        if existing_ref:
            raise HTTPException(status_code=400, detail="Payment reference already exists.")

        new_payout = Payout(
            amount=obj_in.amount,
            bank=obj_in.bank,
            payment_ref=obj_in.payment_ref,
            paid_at=datetime.now(),
            affiliate_id=affiliate_id
        )

        db.add(new_payout)
        db.commit()
        db.refresh(new_payout)

        return new_payout