from uuid import UUID
from app.core.base.services import Service
from app.models.customer import Customer, MockCustomer
from app.schemas.customer import CustomerBase
from sqlalchemy.orm import Session
from sqlalchemy import select, or_

class CustomerService(Service):
    @staticmethod
    def create(db: Session, obj_in: CustomerBase):
        # Logic to create a new customer
        new_customer = MockCustomer(
            first_name=obj_in.first_name,
            last_name=obj_in.last_name,
            email=obj_in.email,
            phone_no=obj_in.phone_no,
            note=obj_in.note
        )

        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        return new_customer
    

    @staticmethod
    def fetch(db: Session, id: UUID):
        return db.get(MockCustomer, id)

    
    @staticmethod
    def fetch_all(db: Session):
        stmt = select(MockCustomer)
        return db.scalars(stmt).all()
    

    @staticmethod
    def search_customers(db: Session, search: str):
        stmt = select(MockCustomer)
        if search:
            search_query = f"%{search}%"

            stmt = stmt.where(
                or_(
                    MockCustomer.first_name.ilike(search_query),
                    MockCustomer.last_name.ilike(search_query),
                    MockCustomer.phone_no.ilike(search_query),
                    MockCustomer.email.ilike(search_query)
                )
            )

            customers = db.execute(stmt).scalars().all()
            return customers
