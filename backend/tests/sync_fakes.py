"""Shared fakes for sync-path tests. Only the Gmail and classifier
boundaries are faked — the service, parsing regexes, and DB code under
test stay real."""
from datetime import datetime

from app.models.schemas import EmailMessage, MerchantCategory
from app.services.transaction_service import TransactionService


class FakeGmailService:
    """Returns one batch of emails per get_messages call, in order."""

    def __init__(self, batches):
        self.batches = list(batches)
        self.queries = []

    def get_messages(self, query):
        self.queries.append(query)
        return self.batches.pop(0) if self.batches else []


class FakeClassifier:
    def __init__(self):
        self.calls = []

    async def classify_merchant(self, merchant):
        self.calls.append(merchant)
        return MerchantCategory(
            primary_category="Food & Dining",
            subcategory="Groceries",
            confidence=0.9,
            description="grocery store",
        )


def make_email(
    message_id,
    merchant="HI-LO GROCERY",
    amount="1,500.00",
    date=datetime(2026, 6, 15, 12, 30),
    parseable=True,
):
    if parseable:
        body = (
            f"Transaction Approved JMD {amount} "
            f"Merchant</div></td><td><div>{merchant}</div>"
        )
    else:
        body = "Transaction Approved - a template the regexes cannot parse"
    return EmailMessage(
        message_id=message_id,
        subject="Transaction Approved",
        sender="no-reply-ncbcardalerts@jncb.com",
        date=date,
        body=body,
    )


def make_service(db, batches):
    return TransactionService(
        gmail_service=FakeGmailService(batches),
        classifier=FakeClassifier(),
        db=db,
    )
