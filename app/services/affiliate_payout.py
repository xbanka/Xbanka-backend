import secrets
from app.core.base.services import Service
from app.core.enums import PayoutStatusEnum
from app.models.customer import Customer
from app.models.payouts import Payout
from app.models.transactions import Transaction
from app.schemas.payout import PayoutRequest

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session


# With timestamp for extra uniqueness (and sortability)
def generate_payout_ref_time() -> str:
    timestamp = datetime.now().strftime("%y%m%d")  # YYMMDD
    random_part = secrets.token_hex(3).upper()  # 6 chars
    return f"PYN-{timestamp}-{random_part}"
    # Returns: PYN-250213-A3F2B8
    

class PayoutService(Service):
    @staticmethod
    def create_new(db: Session, obj_in: PayoutRequest, affiliate_id) -> Payout:

        total_earnings = db.scalar(
            select(func.coalesce(func.sum(Transaction.commission_amount), 0))
            .join(Customer, Customer.id == Transaction.customer_id)
            .where(Customer.affiliate_id == affiliate_id)
        ) or 0

        total_payouts = db.scalar(
            select(func.coalesce(func.sum(Payout.amount), 0))
            .where(Payout.affiliate_id == affiliate_id)
            .where(Payout.status == PayoutStatusEnum.paid)
        ) or 0

        amount_withdrawn = total_payouts
        available_balance = total_earnings - amount_withdrawn
        
        try:
            obj_in.amount = float(obj_in.amount)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid amount format.")
        
        if obj_in.amount <= 0:
            raise HTTPException(status_code=400, detail="Payout amount must be greater than zero.")
        
        if obj_in.amount > available_balance:
            raise HTTPException(status_code=400, detail="Insufficient available balance for this payout.")

        new_payout = Payout(
            amount=obj_in.amount,
            bank=obj_in.bank,
            payment_ref=generate_payout_ref_time(),
            paid_at=datetime.now(),
            affiliate_id=affiliate_id
        )

        db.add(new_payout)
        db.commit()
        db.refresh(new_payout)

        return new_payout