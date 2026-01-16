from uuid import UUID
from app.core.base.services import Service
from app.models.customer import Customer
from app.schemas.customer import CustomerCreateBase
from app.services.affiliate import AffiliateService
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, or_, desc
from app.utils.validators import is_valid_email

class CustomerService(Service):
    @staticmethod
    def create(db: Session, obj_in: CustomerCreateBase):
        # Logic to create a new customer

        if not is_valid_email(obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid email address."
            )
        
        # if email exists
        existing_customer = db.execute(
            select(Customer).where(Customer.email == obj_in.email)
        ).scalar_one_or_none()

        if existing_customer:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Customer with this email already exists."
            )

        customer_affiliate = (
            AffiliateService.get_by_username(db, obj_in.affiliate_username)
            if obj_in.affiliate_username
            else None
        )

        new_customer = Customer(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            email=obj_in.email,
            phone_no=obj_in.phone_no,
            affiliate_id=customer_affiliate.id if customer_affiliate else None
        )

        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        return new_customer
    

    @staticmethod
    def fetch(db: Session, id: UUID):
        return db.get(Customer, id)

    
    @staticmethod
    def fetch_all(db: Session):
        stmt = select(Customer).order_by(desc(Customer.created_at))
        return db.scalars(stmt).all()
    

    @staticmethod
    def search_customers(db: Session, search: str):
        stmt = select(Customer)
        if search:
            search_query = f"%{search}%"

            stmt = stmt.where(
                or_(
                    Customer.first_name.ilike(search_query),
                    Customer.last_name.ilike(search_query),
                    Customer.phone_no.ilike(search_query),
                    Customer.email.ilike(search_query)
                )
            )

            customers = db.execute(stmt).scalars().all()
            return customers
