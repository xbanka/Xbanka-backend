from app.core.base.services import Service
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.affiliate import Affiliate
from app.models.affiliate_monthly_volume import AffiliateMonthlyVolume
from app.models.affiliate_tiers import AffiliateTier
from app.models.tier_volume_bands import TierVolumeBand
from app.schemas.affiliate import AffiliateProgressResponse

class AffiliateProgressService(Service):
    @staticmethod
    def get_affiliate_progress(session: Session, affiliate: Affiliate) -> AffiliateProgressResponse:
        month = date.today().replace(day=1)

        monthly_volume = session.execute(
            select(AffiliateMonthlyVolume).where(
                AffiliateMonthlyVolume.affiliate_id == affiliate.id,
                AffiliateMonthlyVolume.month == month,
            )
        ).scalar_one_or_none()

        total_volume = monthly_volume.total_volume if monthly_volume else Decimal("0.0")

        bands = (
            session.execute(
                select(TierVolumeBand)
                .where(TierVolumeBand.tier_id == affiliate.current_tier_id)
                .order_by(TierVolumeBand.min_volume)
            )
            .scalars()
            .all()
        )

        current_band = None
        next_band = None

        for i, band in enumerate(bands):
            max_volume = band.max_volume or Decimal("999999999999999")
            if band.min_volume <= total_volume <= max_volume:
                current_band = band
                if i + 1 < len(bands):
                    next_band = bands[i + 1]
                break

        amount_to_next_band = None
        if next_band:
            amount_to_next_band = next_band.min_volume - total_volume

        # determine next tier order in order of affiliate rank (1 Bronze, 2 Silver, 3 Gold, 4 Platinum)

        next_tier = (
            session.execute(
                select(AffiliateTier)
                .where(AffiliateTier.rank > affiliate.current_tier.rank)
                .order_by(AffiliateTier.rank)
            )
            .scalars()
            .first()
        )

        return AffiliateProgressResponse(
            current_monthly_volume=total_volume,
            current_band=current_band,
            next_band=next_band,
            next_tier=next_tier,
            amount_to_next_band=amount_to_next_band,
        )
