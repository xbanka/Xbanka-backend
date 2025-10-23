from app.core.base.services import Service
from app.core.enums import StatusEnum
from app.models.affiliate import Affiliate
from app.models.transactions import Transaction
from app.models.customer import Customer

from datetime import datetime, timezone
from fastapi import HTTPException, status
from io import BytesIO
from sqlalchemy import select, func
from sqlalchemy.orm import Session, selectinload
from openpyxl import Workbook
from typing import Optional, cast


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
    def get_commissions(db: Session, affiliate_id, page: int, limit: int, status: Optional[StatusEnum] = None):
        stmt = select(Transaction)

        if status:
            stmt = stmt.where(Transaction.status == status)

        stmt = (
            stmt.options(selectinload(Transaction.customer))
            .join(Customer)
            .where(Customer.affiliate_id == affiliate_id)
            .order_by(Transaction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = db.execute(stmt)
        commissions = result.scalars().all()

        total = db.scalar(
            select(func.count()).select_from(
                select(Transaction)
                .join(Customer)
                .where(Customer.affiliate_id == affiliate_id)
                .subquery()
            )
        ) or 0

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "data": commissions
        }
    
    @staticmethod
    def export_commissions(db: Session, affiliate_id, status: Optional[StatusEnum] = None):
        stmt = select(Transaction)

        if status:
            stmt = stmt.where(Transaction.status == status)

        stmt = (
            stmt.options(selectinload(Transaction.customer))
            .join(Customer)
            .where(Customer.affiliate_id == affiliate_id)
            .order_by(Transaction.created_at.desc())
        )

        commissions = db.execute(stmt).scalars().all()

        wb = Workbook()
        ws = wb.active or wb.create_sheet(title="Commissions")
        ws.title = "Commissions"

        ws.append(
            ["Date", "Type", "Rate", "Amount", "Status", "Customer Name", "Email", "Phone No"]
        )  # header
        
        for tx in commissions:
            # Excel does not support timezone-aware datetime objects
            created_at = cast(datetime, tx.created_at)
            if created_at.tzinfo is not None:
                created_at = created_at.astimezone(timezone.utc).replace(tzinfo=None)

            ws.append([
                created_at,
                tx.transaction_type,
                tx.commission_rate,
                tx.commission_amount,
                tx.status.value,
                tx.customer.first_name + " " + tx.customer.last_name,
                tx.customer.email,
                tx.customer.phone_no,
            ])

        stream = BytesIO()
        wb.save(stream)
        stream.seek(0)

        return stream.getvalue()