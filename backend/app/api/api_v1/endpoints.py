from datetime import datetime
from encodings.aliases import aliases
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import Field

from app.api.api_v1.dependencies import get_transaction_service
from app.models.schemas import (
    Transaction, TransactionSummary, DateRange
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("/transactions/", response_model=List[Transaction])
async def get_transactions(
        startDate: Optional[datetime] = Query(None, alias="startDate"),
        endDate: Optional[datetime] = Query(None, alias="endDate"),
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transactions with optional filters.
    """
    date_range = DateRange(startDate=startDate, endDate=endDate)
    return await service.get_transactions(
        date_range=date_range,
        category=category,
        subcategory=subcategory,
        min_confidence=min_confidence
    )


@router.get("/spending/summary", response_model=TransactionSummary)
async def get_spending_summary(
        startDate: Optional[datetime] = None,
        endDate: Optional[datetime] = None,
        min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get spending summary within date range.
    """
    date_range = DateRange(startDate=startDate, endDate=endDate)
    transactions = await service.get_transactions(
        date_range=date_range,
        min_confidence=min_confidence
    )
    return await service.get_summary(transactions)


@router.get("/categories")
async def get_categories(
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get all available transaction categories.
    """
    transactions = await service.get_transactions()
    categories = {}

    for transaction in transactions:
        if transaction.primary_category not in categories:
            categories[transaction.primary_category] = set()
        categories[transaction.primary_category].add(transaction.subcategory)

    return {k: list(v) for k, v in categories.items()}
