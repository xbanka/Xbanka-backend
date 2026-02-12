from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime
from uuid import UUID

from app.models.affiliate import Affiliate
from app.models.affiliate_commissions import AffiliateCommission
from app.models.affiliate_monthly_volume import AffiliateMonthlyVolume
from app.models.tier_volume_bands import TierVolumeBand

def process_transaction(db: Session, affiliate_id: UUID, transaction_id: UUID, transaction_amount: float, transaction_date: datetime):
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
            AffiliateMonthlyVolume.month == month_start
        )
    )
    if not monthly:
        monthly = AffiliateMonthlyVolume(affiliate_id=affiliate_id, month=month_start)
        db.add(monthly)
        db.flush()  # use flush instead of commit

    # Update monthly volume
    new_total_volume = float(monthly.total_volume) + transaction_amount

    # Get rate from tier bands
    band = db.scalar(
        select(TierVolumeBand).where(
            TierVolumeBand.tier_id == tier.id,
            TierVolumeBand.min_volume <= new_total_volume,
            (TierVolumeBand.max_volume.is_(None)) | (TierVolumeBand.max_volume > new_total_volume)
        )
    )
    rate = band.commission_rate if band else Decimal(0.0)

    # Calculate commission
    commission_amount = Decimal(transaction_amount) * rate

    print(f"type of commission_amount: {type(commission_amount)}, value: {commission_amount}")
    print(f"type of rate: {type(rate)}, value: {rate}")
    print(f"type of monthly total commission: {type(monthly.total_commission)}, value: {monthly.total_commission}")

    # Update monthly totals
    monthly.total_volume = Decimal(new_total_volume)
    monthly.total_commission = Decimal(monthly.total_commission) + Decimal(commission_amount)

    # Store commission trace
    commission = AffiliateCommission(
        transaction_id=transaction_id,
        affiliate_id=affiliate.id,
        commission_amount=commission_amount,
        commission_rate=rate,
        month=month_start
    )
    db.add(commission)
    db.commit()

    return commission
