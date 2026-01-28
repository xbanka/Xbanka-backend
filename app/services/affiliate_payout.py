from app.core.base.services import Service
from app.core.enums import PayoutStatusEnum
from app.models.customer import Customer
from app.models.payouts import Payout
from app.models.transactions import Transaction, TransactionStatusEnum
from app.schemas.payout import PayoutBase

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session

class PayoutService(Service):
    @staticmethod
    def create_new(db: Session, obj_in: PayoutBase, affiliate_id) -> Payout:

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
        
        existing_ref = db.execute(
            select(Payout).where(Payout.payment_ref == obj_in.payment_ref)
        ).scalar_one_or_none()
        
        if existing_ref:
            raise HTTPException(status_code=400, detail="Payment reference already exists.")
        
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
            payment_ref=obj_in.payment_ref,
            paid_at=datetime.now(),
            affiliate_id=affiliate_id
        )

        db.add(new_payout)
        db.commit()
        db.refresh(new_payout)

        return new_payout