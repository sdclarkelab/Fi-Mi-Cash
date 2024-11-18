from functools import lru_cache

from fastapi import Depends

from app.services.classifier_service import MerchantClassifier
from app.services.gmail_service import GmailService
from app.services.transaction_service import TransactionService


@lru_cache()
def get_gmail_service() -> GmailService:
    return GmailService()


@lru_cache()
def get_merchant_classifier() -> MerchantClassifier:
    return MerchantClassifier()


def get_transaction_service(
        gmail_service: GmailService = Depends(get_gmail_service),
        classifier: MerchantClassifier = Depends(get_merchant_classifier)
) -> TransactionService:
    return TransactionService(gmail_service, classifier)
