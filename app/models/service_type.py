from app.core.enums import ServiceTypeEnum
from app.models.base_model import BaseModel
from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship



class ServiceType(BaseModel):
    __tablename__ = 'service_types'

    name: Mapped[ServiceTypeEnum] = mapped_column(Enum(ServiceTypeEnum), nullable=False, index=True)

    transaction_types = relationship("TransactionType", back_populates="service_type")

    def __repr__(self):
        return (
            f"<Service Type(id={self.id}, name={self.name})"
        )
    