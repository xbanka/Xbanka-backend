from app.core.base.services import Service
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from app.models.affiliate import Affiliate
from app.models.affiliate_visit import AffiliateVisit
from app.models.customer import Customer
from app.models.transactions import Transaction
from app.schemas.dashboard import DashboardDisplay

class DashboardService(Service):
    @staticmethod
    def get_summary(db: Session, current_user: Affiliate) -> DashboardDisplay | None:
        stmt = (
            select(
                func.count().label("total_customers"),
                func.sum(case((Customer.converted, 1), else_=0)).label("converted"),
            )
            .where(Customer.affiliate_id == current_user.id)
        )

        result = db.execute(stmt).mappings().first() or {}

        total_commissions = (
            db.query(func.coalesce(func.sum(Transaction.amount_in), 0))
            .join(Transaction.customer)
            .join(Customer.affiliate)
            .filter(Affiliate.id == current_user.id)
            .scalar()
        )

        no_visits = db.execute(
            select(func.count(AffiliateVisit.id)).where(AffiliateVisit.affiliate_id == current_user.id)
        ).scalar() or 0

        # no_visits_2 = db.scalar(
        #     select(func.count()).select_from(
        #         select(AffiliateVisit).where(AffiliateVisit.affiliate_id == current_user.id).subquery()
        #     )
        # ) or 0

        return DashboardDisplay(
            visits=no_visits,
            signed_up=result.get("total_customers", 0) or 0,
            converted=result.get("converted", 0) or 0,
            total_commission=total_commissions
        )


