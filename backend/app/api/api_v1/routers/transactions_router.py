import uuid
from datetime import datetime
from typing import Optional, List
import json

from fastapi import APIRouter, Depends, Query, HTTPException, Body

from app.api.api_v1.dependencies import get_transaction_service
from app.models.schemas import (
    Transaction, DateRange, TransactionList
)
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("/transactions", response_model=TransactionList)
async def get_transactions(
        start_date: datetime = Query(..., alias="startDate"),
        end_date: datetime = Query(..., alias="endDate"),
        categories: List[str] = Query(default=[], description="JSON encoded category filters"),
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
        limit: Optional[int] = Query(default=100, le=1000),
        offset: Optional[int] = Query(default=0, ge=0),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get transactions with optional filters and pagination.
    """
    date_range = DateRange(start_date=start_date, end_date=end_date)
    
    # Parse categories if provided (new multi-select format)
    parsed_categories = []
    if categories:
        try:
            parsed_categories = [json.loads(cat_str) for cat_str in categories]
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid category format")
    
    # Get transactions with pagination
    transactions = await service.get_transactions(
        date_range=date_range,
        categories=parsed_categories if parsed_categories else None,
        category=category,
        subcategory=subcategory,
        min_confidence=min_confidence,
        include_excluded=True,
        limit=limit,
        offset=offset
    )

    # Get summary and categories efficiently using separate queries
    summary = await service.get_summary(transactions)
    categories_data = service.get_categories(
        date_range=date_range,
        categories=parsed_categories if parsed_categories else None,
        category=category,
        subcategory=subcategory,
        min_confidence=min_confidence,
        include_excluded=True
    )

    return TransactionList(transactions=transactions, transaction_summary=summary, categories=categories_data)


@router.get("/transactions/count")
async def get_transaction_count(
        start_date: datetime = Query(..., alias="startDate"),
        end_date: datetime = Query(..., alias="endDate"),
        categories: List[str] = Query(default=[], description="JSON encoded category filters"),
        category: Optional[str] = None,
        subcategory: Optional[str] = None,
        min_confidence: float = Query(default=0.0, ge=0.0, le=1.0),
        service: TransactionService = Depends(get_transaction_service)
):
    """
    Get total count of transactions matching filters.
    """
    date_range = DateRange(start_date=start_date, end_date=end_date)
    
    # Parse categories if provided (new multi-select format)
    parsed_categories = []
    if categories:
        try:
            parsed_categories = [json.loads(cat_str) for cat_str in categories]
        except (json.JSONDecodeError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid category format")
    
    count = service.get_transaction_count(
        date_range=date_range,
        categories=parsed_categories if parsed_categories else None,
        category=category,
        subcategory=subcategory,
        min_confidence=min_confidence,
        include_excluded=True
    )
    return {"count": count}


@router.patch("/transactions/{transaction_id}/toggle-exclude", response_model=Transaction)
async def toggle_transaction_exclusion(
        transaction_id: uuid.UUID,
        excluded: bool = Body(..., embed=True),
        service: TransactionService = Depends(get_transaction_service)
):
    """Toggle whether a transaction is excluded from calculations"""
    transaction = await service.set_transaction_exclusion(transaction_id, excluded)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return transaction
