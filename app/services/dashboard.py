from app.core.base.services import Service
from sqlalchemy import select, func, case
from sqlalchemy.orm import Session
from app.models.affiliate import Affiliate
from app.models.customer import Customer
from app.schemas.dashboard import DashboardDisplay

class DashboardService(Service):
    @staticmethod
    def get_summary(db: Session, current_user: Affiliate) -> DashboardDisplay | None:
        stmt = (
            select(
                func.count().label("total_customers"),
                func.sum(case((Customer.signed_up, 1), else_=0)).label("signed_up"),
                func.sum(case((Customer.converted, 1), else_=0)).label("converted"),
                func.coalesce(func.sum(Customer.commission), 0).label("total_commission"),
            )
            .where(Customer.affiliate_id == current_user.id)
        )

        result = db.execute(stmt).mappings().first() or {}

        return DashboardDisplay(
            total_customers=result.get("total_customers", 0) or 0,
            signed_up=result.get("signed_up", 0) or 0,
            converted=result.get("converted", 0) or 0,
            total_commission=result.get("total_commission", 0) or 0
        )


