from fastapi import HTTPException, status
from psycopg2 import IntegrityError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.core.base.services import Service
from app.core.hash import Hasher
from app.models.affiliate import Affiliate
from app.schemas.user import RegisterBase
from app.utils.validators import is_valid_email, is_valid_password, is_valid_phone


class UserService(Service):
    @staticmethod
    def create(db: Session, obj_in: RegisterBase) -> Affiliate:

        if not is_valid_email(obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Invalid email address.'
            )

        affiliate = db.query(Affiliate).filter_by(email=obj_in.email).first()
        if affiliate:
            raise HTTPException(
                status_code=400,
                detail="Affiliate with email already exists"
            )
    
        if not is_valid_password(obj_in.password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Password must be at least 8 characters long and contain at least one uppercase letter, one lowercase letter, one digit, and one special character.'
            )
        
        if not is_valid_phone(obj_in.phone_no):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Phone number must be a valid Nigerian (+234) or international format'
            )


        try:
            affiliate = Affiliate(
                first_name=obj_in.first_name,
                last_name=obj_in.last_name,
                email=obj_in.email,
                phone_no=obj_in.phone_no,
                bank=obj_in.bank,
                account_no=obj_in.account_no,
                hashed_password=Hasher.get_password_hash(obj_in.password),
                verified=True
            )

            db.add(affiliate)
            db.commit()
            db.refresh(affiliate)
        except IntegrityError as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=400, detail="Database integrity error")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"An error occurred saving entity: {e}")
        except Exception as e:
            print(e)
            db.rollback()
            raise HTTPException(status_code=500, detail="An unknown error occurred")

        return affiliate

    @staticmethod
    def get_user_by_id(db: Session, id: str) -> Affiliate:
        affiliate = db.query(Affiliate).get(id)
        if not affiliate:
            raise HTTPException(
                status_code=404,
                detail="Affiliate not found"
            )
        
        return affiliate
    
    @staticmethod
    def get_user_by_mail(db: Session, email: str) -> Affiliate:
        affiliate = db.query(Affiliate).filter_by(email=email).first()
        if not affiliate:
            raise HTTPException(
                status_code=404,
                detail="affiliate not found"
            )
        
        return affiliate


    @staticmethod
    def get_current_user(db: Session):
        pass