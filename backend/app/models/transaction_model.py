# app/models/transaction_model.py
from sqlalchemy import Column, Integer, String, DateTime, Numeric, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String, index=True)
    primary_category = Column(String, index=True)
    subcategory = Column(String, index=True)
    confidence = Column(Float)
    description = Column(String)