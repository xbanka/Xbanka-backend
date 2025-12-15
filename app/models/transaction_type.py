from app.models.base_model import BaseModel
from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID 
from sqlalchemy.orm import Mapped, mapped_column, relationship



class TransactionType(BaseModel):
    __tablename__ = 'transaction_types'

    name: Mapped[str] = mapped_column(String, nullable=False, index=True)

    service_type_id: Mapped[UUID] = mapped_column(ForeignKey('service_types.id'), nullable=False, index=True)

    service_type = relationship("ServiceType", back_populates="transaction_types")

    def __repr__(self):
        return (
            f"<Transaction Type(id={self.id}, name={self.name}, "
            f"service_type={self.service_type.name if self.service_type else None})>"
        )
    