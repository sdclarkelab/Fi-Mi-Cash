import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException

from app.api.api_v1.dependencies import get_transaction_service
from app.models.schemas import (
    Transaction, DateRange, TransactionList
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("/transactions/", response_model=TransactionList)
async def get_transactions(
        start_date: Optional[datetime] = Query(None, alias="startDate"),
        end_date: Optional[datetime] = Query(None, alias="endDate"),
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transactions with optional filters.
    """
    date_range = DateRange(start_date=start_date, end_date=end_date)
    transactions = await service.get_transactions(
        date_range=date_range,
        category=category,
        subcategory=subcategory,
        min_confidence=min_confidence,
        include_excluded=True
    )

    summary = await service.get_summary(transactions)
    return TransactionList(transactions=transactions, transaction_summary=summary)


@router.patch("/transactions/{transaction_id}/toggle-exclude", response_model=Transaction)
async def toggle_transaction_exclusion(
        transaction_id: uuid.UUID,
        excluded: bool,
        service: TransactionService = Depends(get_transaction_service)
):
    """Toggle whether a transaction is excluded from calculations"""
    transaction = await service.set_transaction_exclusion(transaction_id, excluded)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction


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
