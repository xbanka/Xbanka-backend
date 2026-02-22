from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.base.services import Service
from app.models.affiliate import Affiliate
from app.models.affiliate_monthly_volume import AffiliateMonthlyVolume
from app.models.affiliate_tiers import AffiliateTier
from app.models.affiliate_visit import AffiliateVisit
from app.models.customer import Customer
from app.models.tier_volume_bands import TierVolumeBand
from app.models.transactions import Transaction
from app.schemas.dashboard import DashboardDisplay


class DashboardService(Service):
    @staticmethod
    def get_summary(db: Session, current_user: Affiliate) -> DashboardDisplay | None:
        stmt = select(
            func.count().label("total_customers"),
            func.sum(case((Customer.converted, 1), else_=0)).label("converted"),
        ).where(Customer.affiliate_id == current_user.id)

        result = db.execute(stmt).mappings().first() or {}

        total_commissions = (
            db.query(func.coalesce(func.sum(Transaction.amount_in), 0))
            .join(Transaction.customer)
            .join(Customer.affiliate)
            .filter(Affiliate.id == current_user.id)
            .scalar()
        )

        no_visits = (
            db.execute(
                select(func.count(AffiliateVisit.id)).where(
                    AffiliateVisit.affiliate_id == current_user.id
                )
            ).scalar()
            or 0
        )

        # no_visits_2 = db.scalar(
        #     select(func.count()).select_from(
        #         select(AffiliateVisit).where(AffiliateVisit.affiliate_id == current_user.id).subquery()
        #     )
        # ) or 0

        return DashboardDisplay(
            visits=no_visits,
            signed_up=result.get("total_customers", 0) or 0,
            converted=result.get("converted", 0) or 0,
            total_commission=total_commissions,
        )

    @staticmethod
    def get_affiliate_progress(session: Session, affiliate: Affiliate):
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

        return {
            "total_volume": total_volume,
            "current_band": current_band,
            "next_band": next_band,
            "next_tier": next_tier,
            "amount_to_next_band": amount_to_next_band,
        }
