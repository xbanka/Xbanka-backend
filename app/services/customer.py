from app.core.base.services import Service
from app.models.customer import Customer, MockCustomer
from app.schemas.customer import CustomerBase
from sqlalchemy.orm import Session

class CustomerService(Service):
    @staticmethod
    def create_customer(db: Session, obj_in: CustomerBase):
        # Logic to create a new customer
        new_customer = MockCustomer(
            full_name=obj_in.full_name,
            phone_no=obj_in.phone_no,
            transaction_type=obj_in.transaction_type,
            amount=obj_in.amount,
            note=obj_in.note
        )

        db.add(new_customer)
        db.commit()
        db.refresh(new_customer)
        return new_customer
