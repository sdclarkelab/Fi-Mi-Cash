import re
import uuid
import aiohttp
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.logger import logger
from app.config import get_settings
from app.db.crud import TransactionCrud, SyncInfoCrud
from app.models.schemas import (
    Transaction, TransactionSummary, CategorySummary,
    EmailMessage, DateRange, CreateTransactionRequest
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
            categories: Optional[List[dict]] = None,
            category: Optional[str] = None,
            subcategory: Optional[str] = None,
            min_confidence: float = 0.0,
            include_excluded: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> List[Transaction]:

        # Check if we need to sync with Gmail
        should_sync = await self._should_sync_transactions(date_range)

        if should_sync:
            await self._sync_transactions(date_range)

        # Then retrieve transactions from database with filters
        db_transactions = TransactionCrud.get_transactions(
            self.db, date_range, categories, category, subcategory, min_confidence, include_excluded, limit, offset
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
                excluded=tx.excluded,
                original_currency=tx.original_currency,
                original_amount=Decimal(str(tx.original_amount)) if tx.original_amount else None,
                exchange_rate=Decimal(str(tx.exchange_rate)) if tx.exchange_rate else None,
                exchange_rate_date=tx.exchange_rate_date,
                card_type=tx.card_type
            ) for tx in db_transactions
        ]

    async def _sync_transactions(self, date_range: DateRange):
        """Fetch transactions from Gmail and store in SQLite if not already present"""
        # Only sync the gaps that haven't been synced yet
        sync_gaps = SyncInfoCrud.get_sync_gaps(self.db, date_range)
        
        if not sync_gaps:
            return  # No gaps to sync
            
        for gap in sync_gaps:
            query = self._build_gmail_query(gap)
            emails = self.gmail_service.get_messages(query)

            for email in emails:
                transaction = await self._parse_transaction(email)
                if transaction and not TransactionCrud.transaction_exists(self.db, transaction):
                    TransactionCrud.create_transaction(self.db, transaction)

        # Update the sync info with the originally requested range
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
        card_types = defaultdict(lambda: self._empty_category_summary())

        for transaction in included_transactions:
            self._update_category_summary(
                primary_categories[transaction.primary_category],
                transaction
            )
            self._update_category_summary(
                subcategories[f"{transaction.primary_category} - {transaction.subcategory}"],
                transaction
            )
            if transaction.card_type:
                self._update_category_summary(
                    card_types[transaction.card_type],
                    transaction
                )

        return TransactionSummary(
            total_spending=sum(t.amount for t in included_transactions),
            transaction_count=len(included_transactions),
            average_transaction=sum(t.amount for t in included_transactions) / len(transactions),
            by_primary_category=dict(primary_categories),
            by_subcategory=dict(subcategories),
            by_card_type=dict(card_types),
            merchants=list(set(t.merchant for t in included_transactions))
        )

    async def _get_usd_to_jmd_rate(self, transaction_date: datetime) -> Decimal:
        """
        Fetch USD to JMD exchange rate for a specific date using fawazahmed0's currency API.
        Falls back to latest rate if historical data is not available.
        """
        try:
            # Format date as YYYY-MM-DD for the API
            date_str = transaction_date.strftime("%Y-%m-%d")
            
            # Try to get historical rate for the specific date
            historical_url = f"https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@{date_str}/v1/currencies/usd.json"
            
            async with aiohttp.ClientSession() as session:
                try:
                    # First try historical rate
                    async with session.get(historical_url, timeout=10) as response:
                        if response.status == 200:
                            data = await response.json()
                            jmd_rate = data.get("usd", {}).get("jmd")
                            if jmd_rate:
                                logger.info(f"Using historical USD to JMD rate for {date_str}: {jmd_rate}")
                                return Decimal(str(jmd_rate))
                except (aiohttp.ClientError, KeyError, ValueError):
                    logger.warning(f"Historical rate not available for {date_str}, falling back to latest")
                
                # Fallback to latest rate
                latest_url = "https://cdn.jsdelivr.net/npm/@fawazahmed0/currency-api@latest/v1/currencies/usd.json"
                async with session.get(latest_url, timeout=10) as response:
                    if response.status == 200:
                        data = await response.json()
                        jmd_rate = data.get("usd", {}).get("jmd")
                        if jmd_rate:
                            logger.info(f"Using latest USD to JMD rate for {date_str}: {jmd_rate}")
                            return Decimal(str(jmd_rate))
                        else:
                            raise ValueError("JMD rate not found in API response")
                    else:
                        raise ValueError(f"API returned status {response.status}")
                        
        except Exception as e:
            logger.error(f"Failed to fetch USD to JMD exchange rate: {str(e)}")
            # Fallback to hardcoded rate as last resort
            fallback_rate = Decimal('159')
            logger.warning(f"Using fallback USD to JMD rate: {fallback_rate}")
            return fallback_rate

    @staticmethod
    def _build_gmail_query(date_range: DateRange) -> str:
        settings = get_settings()
        query = 'from:no-reply-ncbcardalerts@jncb.com'

        query += f' after:{int(date_range.start_date.timestamp())}'
        query += f' before:{int(date_range.end_date.timestamp())}'

        query += f' "Transaction Approved" ("{settings.VISA_TYPE}" OR "{settings.MASTERCARD_TYPE}")'
        return query

    async def _parse_transaction(
            self,
            email: EmailMessage
    ) -> Optional[Transaction]:

        try:
            amount = 0.0
            original_currency = None
            original_amount = None
            exchange_rate = None
            exchange_rate_date = None

            amount_pattern = r'(?P<currency>USD|JMD)\s+(?P<amount>[\d,\.]+)'
            amount_match = re.search(amount_pattern, email.body)

            # Get both the currency and amount
            if amount_match:
                currency = amount_match.group('currency')  # Get currency from named group
                raw_amount = Decimal(amount_match.group('amount').replace(',', ''))
                
                # Store original transaction details
                original_currency = currency
                original_amount = raw_amount
                
                if currency == 'USD':
                    # Get historical exchange rate for the transaction date
                    exchange_rate = await self._get_usd_to_jmd_rate(email.date)
                    amount = raw_amount * exchange_rate
                    exchange_rate_date = email.date.date()
                    logger.info(f"Converted USD {raw_amount} to JMD {amount} using rate {exchange_rate} for date {exchange_rate_date}")
                elif currency == 'JMD':
                    amount = raw_amount

            # Pattern for merchant - looks for content between Merchant and /div
            merchant_pattern = r'Merchant</div></td>\s*<td[^>]*><div[^>]*>([^<]+)</div>'
            merchant_match = re.search(merchant_pattern, email.body)
            merchant = merchant_match.group(1).strip() if merchant_match else ""

            # Extract card type from email body using config settings
            settings = get_settings()
            card_type = None
            if settings.MASTERCARD_TYPE in email.body:
                card_type = settings.MASTERCARD_TYPE
            elif settings.VISA_TYPE in email.body:
                card_type = settings.VISA_TYPE

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
                description=classification.description,
                original_currency=original_currency,
                original_amount=original_amount,
                exchange_rate=exchange_rate,
                exchange_rate_date=exchange_rate_date,
                card_type=card_type
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
            by_card_type={},
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
                excluded=tx.excluded,
                original_currency=tx.original_currency,
                original_amount=Decimal(str(tx.original_amount)) if tx.original_amount else None,
                exchange_rate=Decimal(str(tx.exchange_rate)) if tx.exchange_rate else None,
                exchange_rate_date=tx.exchange_rate_date,
                card_type=tx.card_type
            )
        return None

    async def _should_sync_transactions(self, date_range: DateRange = None) -> bool:
        """Determine if we need to sync transactions from Gmail using gap-based logic"""
        if not date_range:
            # If no specific range, check if we've synced today
            last_sync_info = SyncInfoCrud.get_last_sync(self.db)
            if not last_sync_info:
                return True
            today = datetime.now().date()
            return last_sync_info.last_sync_date.date() != today

        # Use gap detection to determine if sync is needed
        sync_gaps = SyncInfoCrud.get_sync_gaps(self.db, date_range)
        return len(sync_gaps) > 0

    def update_category(self, merchant: str, category: str, subcategory: str) -> bool:
        """Update the category for a merchant"""
        updated_count = TransactionCrud.update_transactions_by_merchant(
            self.db, merchant, category, subcategory
        )
        return updated_count > 0

    def get_categories(self, date_range: DateRange, categories: Optional[List[dict]] = None, category: Optional[str] = None, subcategory: Optional[str] = None, min_confidence: float = 0.0, include_excluded: bool = True) -> dict:
        """Get categories efficiently from database"""
        return TransactionCrud.get_categories(
            self.db, date_range, categories, category, subcategory, min_confidence, include_excluded
        )

    def get_transaction_count(self, date_range: DateRange, categories: Optional[List[dict]] = None, category: Optional[str] = None, subcategory: Optional[str] = None, min_confidence: float = 0.0, include_excluded: bool = True) -> int:
        """Get transaction count efficiently from database"""
        return TransactionCrud.get_transaction_count(
            self.db, date_range, categories, category, subcategory, min_confidence, include_excluded
        )

    async def create_manual_transaction(self, request: CreateTransactionRequest) -> Transaction:
        """Create a manually entered transaction"""
        transaction = Transaction(
            id=uuid.uuid4(),
            date=request.date,
            amount=request.amount,
            merchant=request.merchant,
            primary_category=request.primary_category,
            subcategory=request.subcategory,
            confidence=1.0,
            description=request.description or f"Manual entry: {request.merchant}",
            excluded=False,
            original_currency="JMD",
            original_amount=request.amount,
            exchange_rate=None,
            exchange_rate_date=None,
            card_type=request.card_type
        )
        
        TransactionCrud.create_transaction(self.db, transaction)
        return transaction
