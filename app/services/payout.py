from sqlalchemy.orm import Session
from app.core.base.services import Service
from app.models.payouts import Payout
from app.schemas.affiliate import PayoutBase

from datetime import datetime


class PayoutService(Service):
    @staticmethod
    def create_new(db: Session, obj_in: PayoutBase, affiliate_id) -> Payout:
        new_payout = Payout(
            amount=obj_in.amount,
            status=obj_in.status,
            payment_ref=obj_in.payment_ref,
            paid_at=datetime.now(),
            affiliate_id=affiliate_id
        )

        db.add(new_payout)
        db.commit()
        db.refresh(new_payout)

        return new_payout