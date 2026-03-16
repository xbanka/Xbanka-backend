import secrets
from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.core.enums import PayoutStatusEnum, UploadStatusEnum
from app.models.customer import Customer
from app.models.payouts import Payout
from app.models.transactions import Transaction
from app.schemas.payout import PayoutRequest
from app.utils.s3_utils import upload_file, validate_file
from app.utils.settings import settings

S3_BUCKET_NAME = settings.S3_BUCKET_NAME


# With timestamp for extra uniqueness (and sortability)
def generate_payout_ref_time() -> str:
    timestamp = datetime.now().strftime("%y%m%d")  # YYMMDD
    random_part = secrets.token_hex(3).upper()  # 6 chars
    return f"PYN-{timestamp}-{random_part}"
    # Returns: PYN-250213-A3F2B8


class PayoutService(Service):
    @staticmethod
    def create_new(db: Session, obj_in: PayoutRequest, affiliate_id) -> Payout:

        total_earnings = (
            db.scalar(
                select(func.coalesce(func.sum(Transaction.commission_amount), 0))
                .join(Customer, Customer.id == Transaction.customer_id)
                .where(Customer.affiliate_id == affiliate_id)
            )
            or 0
        )

        total_payouts = (
            db.scalar(
                select(func.coalesce(func.sum(Payout.amount), 0))
                .where(Payout.affiliate_id == affiliate_id)
                .where(Payout.status == PayoutStatusEnum.paid)
            )
            or 0
        )

        amount_withdrawn = total_payouts
        available_balance = total_earnings - amount_withdrawn

        try:
            obj_in.amount = float(obj_in.amount)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid amount format.")

        if obj_in.amount <= 0:
            raise HTTPException(
                status_code=400, detail="Payout amount must be greater than zero."
            )

        if obj_in.amount > available_balance:
            raise HTTPException(
                status_code=400,
                detail="Insufficient available balance for this payout.",
            )

        new_payout = Payout(
            amount=obj_in.amount,
            bank=obj_in.bank,
            payment_ref=generate_payout_ref_time(),
            paid_at=datetime.now(),
            affiliate_id=affiliate_id,
        )

        db.add(new_payout)
        db.commit()
        db.refresh(new_payout)

        return new_payout


    @staticmethod
    def upload_attachment(db: Session, payout_id: UUID, attachment: UploadFile):
        transaction = db.get(Transaction, payout_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        try:
            attachment_key = validate_file(attachment, payout_id)
            attachment_url = f"payouts/{attachment_key}"

            upload_file(attachment.file, S3_BUCKET_NAME, attachment_url)

            transaction.attachment_url = attachment_url
            transaction.upload_status = UploadStatusEnum.pending
            db.commit()
            db.refresh(transaction)

            return transaction

        except ClientError as e:
            logging.error(e)
            transaction.upload_status = UploadStatusEnum.failed
            db.commit()

            raise HTTPException(
                status_code=500, detail="An error occured. Attachment upload failed"
            )