import uuid

from sqlalchemy import Column, String, DateTime, Numeric, Float, Boolean, Date

from app.db.base_class import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(DateTime, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String, index=True)
    primary_category = Column(String, index=True)
    subcategory = Column(String, index=True)
    confidence = Column(Float)
    description = Column(String)
    excluded = Column(Boolean, default=False, nullable=False)
    
    # Exchange rate fields for USD transactions
    original_currency = Column(String(3))  # USD, JMD, etc.
    original_amount = Column(Numeric(10, 2))  # Amount in original currency
    exchange_rate = Column(Numeric(10, 6))  # Exchange rate applied
    exchange_rate_date = Column(Date)  # Date the exchange rate was from
