from app.models.affiliate_visit import AffiliateVisit
from datetime import datetime, timedelta
import hashlib
import uuid


def generate_visitor_id() -> str:
    return str(uuid.uuid4())


def generate_fingerprint(ip: str, user_agent: str) -> str:
    raw = f"{ip}:{user_agent}"
    return hashlib.sha256(raw.encode()).hexdigest()


def already_counted_today(db, affiliate_id, visitor_id, fingerprint):
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    query = db.query(AffiliateVisit).filter(
        AffiliateVisit.affiliate_id == affiliate_id,
        AffiliateVisit.created_at >= today_start
    )

    if visitor_id:
        query = query.filter(AffiliateVisit.visitor_id == visitor_id)
    else:
        query = query.filter(AffiliateVisit.fingerprint == fingerprint)

    return db.query(query.exists()).scalar()

