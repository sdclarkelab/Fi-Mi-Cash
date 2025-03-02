# app/db/crud.py
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.transaction_model import TransactionModel
from app.models.schemas import Transaction, DateRange

class TransactionCrud:
    @staticmethod
    def create_transaction(db: Session, transaction: Transaction) -> TransactionModel:
        db_transaction = TransactionModel(
            date=transaction.date,
            amount=transaction.amount,
            merchant=transaction.merchant,
            primary_category=transaction.primary_category,
            subcategory=transaction.subcategory,
            confidence=transaction.confidence,
            description=transaction.description
        )
        db.add(db_transaction)
        db.commit()
        db.refresh(db_transaction)
        return db_transaction

    @staticmethod
    def get_transactions(
            db: Session,
            date_range: Optional[DateRange] = None,
            category: Optional[str] = None,
            subcategory: Optional[str] = None,
            min_confidence: float = 0.0
    ) -> List[TransactionModel]:
        query = db.query(TransactionModel)

        if date_range:
            if date_range.start_date:
                query = query.filter(TransactionModel.date >= date_range.start_date)
            if date_range.end_date:
                query = query.filter(TransactionModel.date <= date_range.end_date)

        if category:
            query = query.filter(TransactionModel.primary_category.ilike(f"%{category}%"))

        if subcategory:
            query = query.filter(TransactionModel.subcategory.ilike(f"%{subcategory}%"))

        if min_confidence > 0:
            query = query.filter(TransactionModel.confidence >= min_confidence)

        return query.all()

    @staticmethod
    def transaction_exists(db: Session, transaction: Transaction) -> bool:
        return db.query(TransactionModel).filter(
            TransactionModel.date == transaction.date,
            TransactionModel.amount == transaction.amount,
            TransactionModel.merchant == transaction.merchant
        ).first() is not None