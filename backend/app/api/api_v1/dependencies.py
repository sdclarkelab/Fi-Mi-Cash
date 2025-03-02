from functools import lru_cache

from fastapi import Depends

from app.services.classifier_service import MerchantClassifier
from app.services.gmail_service import GmailService
from app.services.transaction_service import TransactionService


from sqlalchemy.orm import Session

from app.db.database import get_db


@lru_cache()
def get_gmail_service() -> GmailService:
    return GmailService()


@lru_cache()
def get_merchant_classifier() -> MerchantClassifier:
    return MerchantClassifier()


async def get_transaction_service(
    db: Session = Depends(get_db)
) -> TransactionService:
    gmail_service = GmailService()
    classifier = get_merchant_classifier()  # Use the existing function
    return TransactionService(
        gmail_service=gmail_service,
        classifier=classifier,
        db=db
    )