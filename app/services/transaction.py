from botocore.exceptions import ClientError
import logging
from uuid import UUID

from fastapi import UploadFile, HTTPException
from sqlalchemy import func, select
from app.core.base.services import Service
from app.models.transactions import Transaction
from app.schemas.transactions import TransactionCreatePayload
from sqlalchemy.orm import Session
from app.core.enums import ServiceTypeEnum, UploadStatusEnum
from app.utils.currency import convert_amount, parse_crypto_pair
from app.utils.settings import settings
from app.utils.s3_utils import upload_file, validate_file
from app.services.customer import CustomerService


S3_BUCKET_NAME = settings.S3_BUCKET_NAME

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
                float(obj_in.amount_in), float(xbanka_rate), "USD", getattr(obj_in, "currency")
            )
            currency_in = getattr(obj_in, "currency", None)
            currency_out = "NGN"

        else:
            xbanka_rate, vendor_rate = None, None
            expected_payout = obj_in.amount_in
            currency_in = currency_out = "NGN"

        new_transaction = Transaction(
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
            attachment_url=""
        )

        db.add(new_transaction)
        db.commit()
        db.refresh(new_transaction)
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
        
        total = db.scalar(
            select(func.count()).select_from(
                select(Transaction)
                .subquery()
            )
        ) or 0

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "data": transactions
        }
    
    @staticmethod
    def upload_attachment(db: Session, transaction_id: UUID, attachment: UploadFile):
        transaction = db.get(Transaction, transaction_id)
        if not transaction:
            raise HTTPException(status_code=404, detail="Transaction not found.")
        
        try:
            attachment_url = validate_file(attachment, transaction_id)
        
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

            raise HTTPException(status_code=500, detail="An error occured. Attachment upload failed")
