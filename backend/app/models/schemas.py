from datetime import datetime
from decimal import Decimal
from typing import List, Optional, Dict
from uuid import uuid4

from pydantic import BaseModel, Field


class EmailMessage(BaseModel):
    subject: str
    sender: str
    date: datetime
    body: str


class MerchantCategory(BaseModel):
    primary_category: str
    subcategory: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str


class Transaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    date: datetime
    amount: Decimal = Field(decimal_places=2)
    merchant: str
    primary_category: str
    subcategory: str
    confidence: float = Field(ge=0.0, le=1.0)
    description: str

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }

class CategorySummary(BaseModel):
    total: Decimal
    count: int
    average: Decimal
    merchants: List[str]


class TransactionSummary(BaseModel):
    total_spending: Decimal
    transaction_count: int
    average_transaction: Decimal
    by_primary_category: Dict[str, CategorySummary]
    by_subcategory: Dict[str, CategorySummary]
    merchants: List[str]

    class Config:
        json_encoders = {
            Decimal: lambda v: float(v)
        }


class DateRange(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class TransactionList(BaseModel):
    transaction_summary: TransactionSummary
    transactions: List[Transaction]