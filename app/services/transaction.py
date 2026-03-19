import logging
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from botocore.exceptions import ClientError
from fastapi import HTTPException, UploadFile
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.core.enums import ServiceTypeEnum, UploadStatusEnum
from app.models.affiliate import Affiliate
from app.models.affiliate_commissions import AffiliateCommission
from app.models.affiliate_monthly_volume import AffiliateMonthlyVolume
from app.models.tier_volume_bands import TierVolumeBand
from app.models.transactions import Transaction
from app.schemas.transactions import TransactionCreatePayload
from app.services.customer import CustomerService
from app.utils.currency import convert_amount, parse_crypto_pair
from app.utils.s3_utils import upload_file, validate_file
from app.utils.settings import settings

S3_BUCKET_TRANSACTIONS = settings.S3_BUCKET_TRANSACTIONS


def generate_txn_id(db):
    year = datetime.now().year
    seq = db.execute(text(f"SELECT nextval('txn_{year}_seq')")).scalar()

    return f"TX-{year}{str(seq).zfill(5)}"


class TransactionService(Service):
    @staticmethod
    def create(db: Session, obj_in: TransactionCreatePayload):
        customer = CustomerService.fetch(db, obj_in.customer_id)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")

        affiliate_username = customer.affiliate.username if customer.affiliate else None

        if obj_in.service_type == ServiceTypeEnum.crypto:
            # Calculate expected payout for crypto and gift card transactions
            xbanka_rate = getattr(obj_in, "xbanka_rate")
            vendor_rate = getattr(obj_in, "vendor_rate")

            crypto_pair = getattr(obj_in, "crypto_pair")
            # xbanka_account = getattr(obj_in, "xbanka_account")
            currency_in, currency_out = parse_crypto_pair(crypto_pair)
            expected_payout = convert_amount(
                float(obj_in.amount_in), float(xbanka_rate), currency_in, currency_out
            )
        elif obj_in.service_type == ServiceTypeEnum.gift_card:
            xbanka_rate = getattr(obj_in, "xbanka_rate")
            vendor_rate = getattr(obj_in, "vendor_rate")

            expected_payout = convert_amount(
                float(obj_in.amount_in),
                float(xbanka_rate),
                "USD",
                getattr(obj_in, "currency"),
            )
            currency_in = getattr(obj_in, "currency", None)
            currency_out = "NGN"

        else:
            xbanka_rate, vendor_rate = None, None
            expected_payout = obj_in.amount_in
            currency_in = currency_out = "NGN"

        new_transaction = Transaction(
            txn_id=generate_txn_id(db=db),
            service_type=obj_in.service_type,
            amount_in=obj_in.amount_in,
            amount_out=expected_payout,
            affiliate_source=affiliate_username,
            xbanka_rate=xbanka_rate,
            vendor_rate=vendor_rate,
            customer_account=obj_in.customer_account,
            vendor=obj_in.vendor,
            xbanka_account=getattr(obj_in, "xbanka_account", None),
            crypto_pair=getattr(obj_in, "crypto_pair", None),
            gift_card_type=getattr(obj_in, "gift_card_type", None),
            gift_card_code=getattr(obj_in, "gift_card_code", None),
            currency_in=currency_in,
            currency_out=currency_out,
            quantity=getattr(obj_in, "quantity", None),
            customer_id=obj_in.customer_id,
            attachment_url="",
        )

        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)

        if customer.affiliate:
            try:
                TransactionService.process_commission(
                    db=db,
                    affiliate_id=customer.affiliate.id,
                    transaction_id=UUID(str(new_transaction.id)),
                    transaction_amount=float(new_transaction.amount_in),
                    transaction_date=date.today(),
                )
            except ValueError as e:
                logging.error(f"Error processing transaction for affiliate tier: {e}")

        return new_transaction

    @staticmethod
    def fetch(db: Session, id: UUID):
        return db.get(Transaction, id)

    @staticmethod
    def fetch_all_paginated(db: Session, page: int, limit: int):
        stmt = select(Transaction)
        stmt = (
            stmt.order_by(Transaction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = db.execute(stmt)
        transactions = result.scalars().all()

        total = (
            db.scalar(select(func.count()).select_from(select(Transaction).subquery()))
            or 0
        )

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "data": transactions,
        }

    @staticmethod
    def fetch_by_customer_paginated(db: Session, customer_id: UUID):
        stmt = (
            select(Transaction)
            .order_by(Transaction.created_at.desc())
            .where(Transaction.customer_id == customer_id)
        )

        transactions = db.execute(stmt).scalars().all()
        return transactions

    @staticmethod
    def upload_attachment(db: Session, transaction_id: UUID, attachment: UploadFile):
        transaction = db.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found.")

        try:
            attachment_key = validate_file(attachment, transaction_id)
            attachment_url = f"transactions/{attachment_key}"

            upload_file(attachment.file, S3_BUCKET_TRANSACTIONS, attachment_url)

            transaction.attachment_url = attachment_url
            transaction.upload_status = UploadStatusEnum.completed
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

    @staticmethod
    def process_commission(
        db: Session,
        affiliate_id: UUID,
        transaction_id: UUID,
        transaction_amount: float,
        transaction_date: date,
    ):
        month_start = transaction_date.replace(day=1)

        # 1️⃣ Get affiliate and tier
        affiliate = db.get(Affiliate, affiliate_id)
        tier = affiliate.current_tier if affiliate else None
        if not affiliate or not tier:
            raise ValueError("Affiliate or tier not found")

        # Get or create monthly volume record
        monthly = db.scalar(
            select(AffiliateMonthlyVolume).where(
                AffiliateMonthlyVolume.affiliate_id == affiliate_id,
                AffiliateMonthlyVolume.month == month_start,
            )
        )
        if not monthly:
            monthly = AffiliateMonthlyVolume(
                affiliate_id=affiliate_id, month=month_start
            )
            db.add(monthly)
            db.flush()  # use flush instead of commit

        # Update monthly volume
        new_total_volume = float(monthly.total_volume) + transaction_amount

        # Get rate from tier bands
        band = db.scalar(
            select(TierVolumeBand).where(
                TierVolumeBand.tier_id == tier.id,
                TierVolumeBand.min_volume <= new_total_volume,
                (TierVolumeBand.max_volume.is_(None))
                | (TierVolumeBand.max_volume > new_total_volume),
            )
        )
        rate = band.commission_rate if band else Decimal(0.0)

        # Calculate commission
        commission_amount = Decimal(transaction_amount) * rate

        # Update monthly totals
        monthly.total_volume = Decimal(new_total_volume)
        monthly.total_commission = Decimal(monthly.total_commission) + Decimal(
            commission_amount
        )

        # Store commission trace
        commission = AffiliateCommission(
            transaction_id=transaction_id,
            affiliate_id=affiliate.id,
            commission_amount=commission_amount,
            commission_rate=rate,
            month=month_start,
        )
        db.add(commission)
        db.commit()

        return commission
