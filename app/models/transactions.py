from app.core.enums import StatusEnum
from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, String, Enum, DECIMAL, Integer
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Transaction(BaseModel):
    __tablename__ = 'transactions'

    affiliate_source: Mapped[str] = mapped_column(String, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    commission_rate: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[Enum] = mapped_column(Enum(StatusEnum), default=StatusEnum.pending, nullable=False)

    customer_id: Mapped[UUID] = mapped_column(ForeignKey('customers.id'), nullable=False, index=True)

    customer = relationship("Customer", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, customer_id={self.customer_id}, "
            f"transaction_type='{self.transaction_type}', commission_rate={self.commission_rate}, "
            f"commission_amount={self.commission_amount}, status='{self.status}')>"
        )
    