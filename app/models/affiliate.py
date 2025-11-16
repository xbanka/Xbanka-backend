from app.models.base_model import BaseModel
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

class Affiliate(BaseModel):
    __tablename__ = 'affiliates'

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=True, index=True)
    phone_no: Mapped[str] = mapped_column(String(50), nullable=False)
    bank: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    account_no: Mapped[str] = mapped_column(String(50), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    ref_code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    custom_refcode: Mapped[str] = mapped_column(String(50), nullable=True, unique=True)

    customers = relationship("Customer", back_populates="affiliate")

    payouts = relationship("Payout", back_populates="affiliate")

    def __repr__(self):
        return f"<Affiliate(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}', phone_no='{self.phone_no}', bank='{self.bank}', account_no='{self.account_no}', is_verified={self.verified})>"