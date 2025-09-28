from app.models.base_model import BaseModel
from sqlalchemy import Column, String

class User(BaseModel):
    __tablename__ = 'users'

    first_name = Column(String(100), nullable=False, index=True)
    last_name = Column(String(100), nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone_no = Column(String(50), nullable=False)
    bank = Column(String(50), nullable=False, index=True)
    account_no = Column(String(50), nullable=False)
    hashed_password = Column(String(255), nullable=False)

    def __repr__(self):
        return f"<User(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}', phone_no='{self.phone_no}', bank='{self.bank}', account_no='{self.account_no}')>"