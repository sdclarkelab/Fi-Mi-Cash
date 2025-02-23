import re
from collections import defaultdict
from decimal import Decimal
from typing import List, Optional

from app.core.logger import logger
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
            classifier: MerchantClassifier
    ):
        self.gmail_service = gmail_service
        self.classifier = classifier

    async def get_transactions(
            self,
            date_range: Optional[DateRange] = None,
            category: Optional[str] = None,
            subcategory: Optional[str] = None,
            min_confidence: float = 0.0
    ) -> List[Transaction]:
        query = self._build_gmail_query(date_range)
        emails = self.gmail_service.get_messages(query)

        transactions = []
        for email in emails:
            transaction = await self._parse_transaction(email)
            if transaction and self._matches_filters(
                    transaction, category, subcategory, min_confidence
            ):
                transactions.append(transaction)

        return transactions

    async def get_summary(
            self,
            transactions: List[Transaction]
    ) -> TransactionSummary:
        if not transactions:
            return self._empty_summary()

        primary_categories = defaultdict(lambda: self._empty_category_summary())
        subcategories = defaultdict(lambda: self._empty_category_summary())

        for transaction in transactions:
            self._update_category_summary(
                primary_categories[transaction.primary_category],
                transaction
            )
            self._update_category_summary(
                subcategories[f"{transaction.primary_category} - {transaction.subcategory}"],
                transaction
            )

        return TransactionSummary(
            total_spending=sum(t.amount for t in transactions),
            transaction_count=len(transactions),
            average_transaction=sum(t.amount for t in transactions) / len(transactions),
            by_primary_category=dict(primary_categories),
            by_subcategory=dict(subcategories),
            merchants=list(set(t.merchant for t in transactions))
        )

    def _build_gmail_query(self, date_range: Optional[DateRange]) -> str:
        query = 'from:no-reply-ncbcardalerts@jncb.com'

        if date_range:
            if date_range.start_date:
                query += f' after:{int(date_range.start_date.timestamp())}'
            if date_range.end_date:
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
                    amount = Decimal(amount_match.group('amount').replace(',', '')) * Decimal('158')
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

    def _matches_filters(
            self,
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
