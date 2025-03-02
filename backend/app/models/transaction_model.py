import uuid

from sqlalchemy import Column, String, DateTime, Numeric, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


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
