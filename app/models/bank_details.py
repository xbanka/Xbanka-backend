from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.models.base_model import BaseModel


class BankDetails(BaseModel):
    __tablename__ = "bank_details"

    bank_name = Column(String(255), nullable=False)
    account_number = Column(String(127), nullable=False)
    # account_name = Column(String(255), nullable=False)
    affiliate_id = Column(
        UUID, ForeignKey("affiliates.id", ondelete="CASCADE"), nullable=False
    )

    affiliate = relationship("Affiliate", back_populates="bank_details")

    def __repr__(self):
        return f"<BankDetails(bank_name='{self.bank_name}', account_number='{self.account_number}', account_name='{self.account_name}')>"
