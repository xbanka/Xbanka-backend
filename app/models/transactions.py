from app.models.base_model import BaseModel
from sqlalchemy import String, Enum, DECIMAL, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


status_enum = Enum("Approved", "Pending", "Active", name="status_enum")

class Transaction(BaseModel):
    __tablename__ = 'transactions'

    id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    affiliate_source: Mapped[str] = mapped_column(String, nullable=True)
    customer_id: Mapped[UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String, nullable=False)
    commission_rate: Mapped[float] = mapped_column(DECIMAL(12, 2), nullable=False)
    commission_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[Enum] = mapped_column(status_enum, nullable=False)
    