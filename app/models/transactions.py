from app.core.enums import TransactionStatusEnum
from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, String, Enum, DECIMAL, Computed
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.orm import Mapped, mapped_column, relationship


class Transaction(BaseModel):
    __tablename__ = 'transactions'

    affiliate_source: Mapped[str] = mapped_column(String, nullable=True)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    transaction_amount: Mapped[int] = mapped_column(DECIMAL(12, 2), nullable=False)
    commission_rate: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    commission_amount: Mapped[int] = mapped_column(
        DECIMAL(12, 2), 
        Computed("transaction_amount * commission_rate / 100", persisted=True), 
        nullable=False
    )
    status: Mapped[TransactionStatusEnum] = mapped_column(Enum(TransactionStatusEnum), default=TransactionStatusEnum.pending, nullable=False)

    amount_in: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    amount_out: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    margin: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)

    vendor_rate: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    xbanka_rate: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)

    customer_id: Mapped[UUID] = mapped_column(ForeignKey('customers.id'), nullable=False, index=True)

    customer = relationship("Customer", back_populates="transactions")

    def __repr__(self):
        return (
            f"<Transaction(id={self.id}, customer_id={self.customer_id}, "
            f"transaction_type='{self.transaction_type}', commission_rate={self.commission_rate}, "
            f"commission_amount={self.commission_amount}, status='{self.status}')>"
        )
    