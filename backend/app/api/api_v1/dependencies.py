import secrets
from functools import lru_cache

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.database import get_db
from app.services.classifier_service import MerchantClassifier
from app.services.gmail_service import GmailService
from app.services.transaction_service import TransactionService


_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    settings = get_settings()
    if api_key is None or not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )


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


_classifier = None


def get_classifier():
    global _classifier
    if _classifier is None:
        _classifier = MerchantClassifier()
    return _classifier
