from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base_model import BaseModel


class Customer(BaseModel):
    __tablename__ = "customers"

    first_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, nullable=False, index=True
    )
    phone_no: Mapped[str] = mapped_column(String(50), nullable=True)
    converted: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True
    )  # has performed Transaction?
    conversion_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # time of first transaction

    affiliate_id: Mapped[UUID] = mapped_column(
        ForeignKey("affiliates.id"), nullable=True, index=True
    )

    affiliate = relationship("Affiliate", back_populates="customers")

    transactions = relationship(
        "Transaction",
        back_populates="customer",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    # chat_rooms = relationship(
    #     "ChatRoom",
    #     back_populates="support_agent",
    #     cascade="all, delete-orphan",
    #     passive_deletes=True,
    # )

    def __repr__(self):
        return f"<Customer(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}')>"


class MockCustomer(BaseModel):
    __tablename__ = "mock_customers"

    first_name: Mapped[str] = mapped_column(String(200), nullable=False)
    last_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(120), nullable=False)
    phone_no: Mapped[str] = mapped_column(String(50), nullable=False)
    note: Mapped[str] = mapped_column(String(255), nullable=True)

    def __repr__(self):
        return f"<MockCustomer(first_name='{self.first_name}', last_name='{self.last_name}', email='{self.email}', phone_no='{self.phone_no}', note='{self.note}')>"
