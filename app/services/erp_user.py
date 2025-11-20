from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from psycopg2 import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.base.services import Service
from app.core.enums import PayoutStatusEnum
from app.core.hash import Hasher
from app.models.erp_user import ERPUser
from app.models.notifications import Notification

from app.models.payouts import Payout
from app.schemas.erp.user import RegisterBase
from app.utils.validators import is_valid_email, is_valid_password


class ERPService(Service):
    @staticmethod
    def create(db: Session, obj_in: RegisterBase) -> ERPUser:
        if not is_valid_email(obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )

        stmt = select(ERPUser).where(ERPUser.email == obj_in.email)
        erp_user = db.execute(stmt).scalars().first()

        if erp_user:
            raise HTTPException(
                status_code=400, detail="ERP user with email/username already exists"
            )

        if not is_valid_password(obj_in.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.",
            )

        try:
            erp_user = ERPUser(
                first_name=obj_in.first_name,
                last_name=obj_in.last_name,
                email=obj_in.email,
                hashed_password=Hasher.get_password_hash(obj_in.password),
                verified=False,
            )

            db.add(erp_user)
            db.commit()
            db.refresh(erp_user)
        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(
                status_code=500, detail=f"An error occurred saving entity: {e}"
            )
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return erp_user

    @staticmethod
    def get_user_by_id(db: Session, id: str) -> ERPUser:
        erp_user = db.query(ERPUser).get(id)
        if not erp_user:
            raise HTTPException(status_code=404, detail="ERP user not found")

        return erp_user

    @staticmethod
    def get_user_by_mail(db: Session, email: str) -> ERPUser:
        erp_user = db.query(ERPUser).filter_by(email=email).first()
        if not erp_user:
            raise HTTPException(status_code=404, detail="ERP user not found")

        return erp_user

    @staticmethod
    def get_current_user(db: Session):
        pass

    @staticmethod
    def get_notifications(db: Session, current_user: ERPUser):
        stmt = (
            select(Notification)
            .where(Notification.user_id == current_user.id)
            .join(ERPUser)
        )
        notifications = db.execute(stmt).scalars().all()
        return notifications
    
    @staticmethod
    def mark_notification_as_read(db: Session, id: UUID, current_user: ERPUser):
        notif = db.get(Notification, id)
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found"
            )
        
        if notif.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not allowed to access this resource"
            )

        notif.is_read = True
        notif.read_at = datetime.now()
        db.commit()
        db.refresh(notif)
        return notif
    

    @staticmethod
    def get_all_payouts(db: Session, page: int, limit: int, status: Optional[PayoutStatusEnum] = None):
        stmt = select(Payout)

        if status:
            stmt = stmt.where(Payout.status == status)

        stmt = (
            stmt.order_by(Payout.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )

        result = db.execute(stmt)
        payouts = result.scalars().all()

        total = db.scalar(
            select(func.count()).select_from(
                select(Payout)
                .subquery()
            )
        ) or 0

        return {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit,
            "data": payouts
        }
