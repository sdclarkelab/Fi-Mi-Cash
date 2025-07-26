import re
import uuid
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.db.crud import TransactionCrud, SyncInfoCrud
from app.models.schemas import (
    Transaction, TransactionSummary, CategorySummary,
    EmailMessage, DateRange
)
from app.services.classifier_service import MerchantClassifier
from app.services.gmail_service import GmailService


class TransactionService:
    def __init__(
            self,
            gmail_service: GmailService,
            classifier: MerchantClassifier,
            db: Session
    ):
        self.gmail_service = gmail_service
        self.classifier = classifier
        self.db = db

    async def get_transactions(
            self,
            date_range: DateRange,
            category: Optional[str] = None,
            subcategory: Optional[str] = None,
            min_confidence: float = 0.0,
            include_excluded: bool = True
    ) -> List[Transaction]:

        # Check if we need to sync with Gmail
        should_sync = await self._should_sync_transactions(date_range)

        if should_sync:
            await self._sync_transactions(date_range)

        # Then retrieve transactions from database with filters
        db_transactions = TransactionCrud.get_transactions(
            self.db, date_range, category, subcategory, min_confidence, include_excluded
        )

        # Convert DB models to Pydantic models
        return [
            Transaction(
                id=uuid.UUID(tx.id),
                date=tx.date,
                amount=Decimal(str(tx.amount)),
                merchant=tx.merchant,
                primary_category=tx.primary_category,
                subcategory=tx.subcategory,
                confidence=tx.confidence,
                description=tx.description,
                excluded=tx.excluded
            ) for tx in db_transactions
        ]

    async def _sync_transactions(self, date_range: DateRange):
        """Fetch transactions from Gmail and store in SQLite if not already present"""
        query = self._build_gmail_query(date_range)
        emails = self.gmail_service.get_messages(query)

        for email in emails:
            transaction = await self._parse_transaction(email)
            if transaction and not TransactionCrud.transaction_exists(self.db, transaction):
                TransactionCrud.create_transaction(self.db, transaction)

        # Update the sync info
        start_date = date_range.start_date if date_range else None
        end_date = date_range.end_date if date_range else None
        SyncInfoCrud.update_last_sync(self.db, start_date, end_date)

    async def get_summary(
            self,
            transactions: List[Transaction]
    ) -> TransactionSummary:
        if not transactions:
            return self._empty_summary()

        included_transactions = [t for t in transactions if not t.excluded]

        if not included_transactions:
            return self._empty_summary()

        primary_categories = defaultdict(lambda: self._empty_category_summary())
        subcategories = defaultdict(lambda: self._empty_category_summary())

        for transaction in included_transactions:
            self._update_category_summary(
                primary_categories[transaction.primary_category],
                transaction
            )
            self._update_category_summary(
                subcategories[f"{transaction.primary_category} - {transaction.subcategory}"],
                transaction
            )

        return TransactionSummary(
            total_spending=sum(t.amount for t in included_transactions),
            transaction_count=len(included_transactions),
            average_transaction=sum(t.amount for t in included_transactions) / len(transactions),
            by_primary_category=dict(primary_categories),
            by_subcategory=dict(subcategories),
            merchants=list(set(t.merchant for t in included_transactions))
        )

    @staticmethod
    def _build_gmail_query(date_range: DateRange) -> str:
        query = 'from:no-reply-ncbcardalerts@jncb.com'

        query += f' after:{int(date_range.start_date.timestamp())}'
        query += f' before:{int(date_range.end_date.timestamp())}'

        query += ' "Transaction Approved" ("NCB VISA PLATINUM" OR "MASTERCARD PLATINUM USD")'
        return query

    async def _parse_transaction(
            self,
            email: EmailMessage
    ) -> Optional[Transaction]:

        try:
            amount = 0.0

            amount_pattern = r'(?P<currency>USD|JMD)\s+(?P<amount>[\d,\.]+)'
            amount_match = re.search(amount_pattern, email.body)

            # Get both the currency and amount
            if amount_match:
                currency = amount_match.group('currency')  # Get currency from named group
                # Remove commas from amount and convert to float
                if currency == 'USD':
                    amount = Decimal(amount_match.group('amount').replace(',', '')) * Decimal('159')
                elif currency == 'JMD':
                    amount = Decimal(amount_match.group('amount').replace(',', ''))

            # Pattern for merchant - looks for content between Merchant and /div
            merchant_pattern = r'Merchant</div></td>\s*<td[^>]*><div[^>]*>([^<]+)</div>'
            merchant_match = re.search(merchant_pattern, email.body)
            merchant = merchant_match.group(1).strip() if merchant_match else ""

            if not amount or not merchant:
                logger.warning(f"Failed to parse transaction from email dated {email.date}")
                return None

            classification = await self.classifier.classify_merchant(merchant)

            return Transaction(
                id=uuid.uuid4(),
                date=email.date,
                amount=amount,
                merchant=merchant,
                primary_category=classification.primary_category,
                subcategory=classification.subcategory,
                confidence=classification.confidence,
                description=classification.description
            )
        except Exception as e:
            logger.error(f"Error processing transaction: {str(e)}")
            return None

    @staticmethod
    def _matches_filters(
            transaction: Transaction,
            category: Optional[str],
            subcategory: Optional[str],
            min_confidence: float
    ) -> bool:
        if min_confidence and transaction.confidence < min_confidence:
            return False
        if category and transaction.primary_category.lower() != category.lower():
            return False
        if subcategory and transaction.subcategory.lower() != subcategory.lower():
            return False
        return True

    def _empty_category_summary(self) -> CategorySummary:
        return CategorySummary(
            total=Decimal('0'),
            count=0,
            average=Decimal('0'),
            merchants=[]
        )

    def _empty_summary(self) -> TransactionSummary:
        return TransactionSummary(
            total_spending=Decimal('0'),
            transaction_count=0,
            average_transaction=Decimal('0'),
            by_primary_category={},
            by_subcategory={},
            merchants=[]
        )

    def _update_category_summary(
            self,
            summary: CategorySummary,
            transaction: Transaction
    ) -> None:
        summary.total += transaction.amount
        summary.count += 1
        summary.average = summary.total / summary.count
        if transaction.merchant not in summary.merchants:
            summary.merchants.append(transaction.merchant)

    async def set_transaction_exclusion(self, transaction_id: uuid.UUID, excluded: bool) -> Optional[Transaction]:
        """Set the exclusion status of a transaction"""
        tx = TransactionCrud.set_exclusion(self.db, transaction_id, excluded)
        if tx:
            return Transaction(
                id=uuid.UUID(tx.id),
                date=tx.date,
                amount=Decimal(str(tx.amount)),
                merchant=tx.merchant,
                primary_category=tx.primary_category,
                subcategory=tx.subcategory,
                confidence=tx.confidence,
                description=tx.description,
                excluded=tx.excluded
            )
        return None

    async def _should_sync_transactions(self, date_range: DateRange = None) -> bool:
        """Determine if we need to sync transactions from Gmail"""
        # Get the last sync info
        last_sync_info = SyncInfoCrud.get_last_sync(self.db)

        # If no previous sync, we should sync now
        if not last_sync_info:
            return True

        # If no specific date range requested, check if we've synced today
        if not date_range:
            today = datetime.now().date()
            return last_sync_info.last_sync_date.date() != today

        # Convert datetime objects to naive before comparison
        def to_naive(dt):
            if dt and dt.tzinfo:
                return dt.replace(tzinfo=None)
            return dt

        # Get normalized datetime objects
        start_date = to_naive(date_range.start_date) if date_range.start_date else None
        end_date = to_naive(date_range.end_date) if date_range.end_date else None
        last_start = to_naive(last_sync_info.start_date) if last_sync_info.start_date else None
        last_end = to_naive(last_sync_info.end_date) if last_sync_info.end_date else None

        # Check if requested dates are outside our last sync range
        if start_date and (not last_start or start_date < last_start):
            return True

        if end_date and (not last_end or end_date > last_end):
            return True

        return False

    def update_category(self, merchant: str, category: str, subcategory: str) -> bool:
        """Update the category for a merchant"""
        updated_count = TransactionCrud.update_transactions_by_merchant(
            self.db, merchant, category, subcategory
        )
        return updated_count > 0
