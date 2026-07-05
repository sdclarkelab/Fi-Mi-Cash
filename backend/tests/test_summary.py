import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from app.models.schemas import Transaction
from app.services.transaction_service import TransactionService


def make_transaction(merchant, amount, category, excluded=False):
    return Transaction(
        id=uuid.uuid4(),
        date=datetime(2026, 6, 15, 12, 30),
        amount=Decimal(amount),
        merchant=merchant,
        primary_category=category,
        subcategory="General",
        confidence=0.9,
        description="test",
        excluded=excluded,
    )


# get_summary touches neither Gmail, the classifier, nor the DB.
SERVICE = TransactionService(gmail_service=None, classifier=None, db=None)


def test_top_spending_category_is_largest_total():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries"),
        make_transaction("PRICESMART", "2000.00", "Groceries"),
        make_transaction("COFFEE SPOT", "500.00", "Dining"),
    ]))
    assert summary.top_spending_category == "Groceries"
    assert summary.top_spending_category_amount == Decimal("3000.00")


def test_top_spending_category_ignores_excluded():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries"),
        make_transaction("CASINO", "9000.00", "Entertainment", excluded=True),
    ]))
    assert summary.top_spending_category == "Groceries"
    assert summary.top_spending_category_amount == Decimal("1000.00")


def test_top_spending_category_none_when_empty():
    summary = asyncio.run(SERVICE.get_summary([]))
    assert summary.top_spending_category is None
    assert summary.top_spending_category_amount is None


def test_top_spending_category_none_when_all_excluded():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries", excluded=True),
    ]))
    assert summary.top_spending_category is None
