import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models.schemas import Transaction, DateRange
from app.models.sync_info_model import SyncInfoModel
from app.models.transaction_model import TransactionModel


class TransactionCrud:
    @staticmethod
    def create_transaction(db: Session, transaction: Transaction) -> TransactionModel:
        transaction_id = transaction.id if hasattr(transaction, 'id') else uuid.uuid4()

        db_transaction = TransactionModel(
            id=str(transaction_id),
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
            min_confidence: float = 0.0,
            include_excluded: bool = True
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

        if not include_excluded:
            query = query.filter(TransactionModel.excluded == False)

        return query.order_by(TransactionModel.date.desc()).all()

    @staticmethod
    def transaction_exists(db: Session, transaction: Transaction) -> bool:
        return db.query(TransactionModel).filter(
            TransactionModel.date == transaction.date,
            TransactionModel.amount == transaction.amount,
            TransactionModel.merchant == transaction.merchant
        ).first() is not None

    @staticmethod
    def set_exclusion(db: Session, transaction_id: uuid.UUID, excluded: bool) -> Optional[TransactionModel]:
        transaction = db.query(TransactionModel).filter(TransactionModel.id == str(transaction_id)).first()
        if transaction:
            transaction.excluded = excluded
            db.commit()
            db.refresh(transaction)
        return transaction

    # app/crud/transaction.py
    @staticmethod
    def update_transactions_by_merchant(db: Session, merchant: str, category: str, subcategory: str):
        """Update the classification of all transactions with matching merchant name"""
        try:
            updated_count = db.query(TransactionModel).filter(
                TransactionModel.merchant == merchant
            ).update({
                "primary_category": category,
                "subcategory": subcategory
            })
            db.commit()
            return updated_count
        except Exception as e:
            db.rollback()
            return 0


class SyncInfoCrud:
    @staticmethod
    def get_last_sync(db: Session) -> Optional[SyncInfoModel]:
        return db.query(SyncInfoModel).filter(SyncInfoModel.id == "last_sync").first()

    @staticmethod
    def update_last_sync(db: Session, start_date: Optional[datetime], end_date: Optional[datetime]) -> SyncInfoModel:
        sync_info = db.query(SyncInfoModel).filter(SyncInfoModel.id == "last_sync").first()

        # Helper function to make datetime objects timezone-naive
        def to_naive(dt):
            if dt and dt.tzinfo:
                return dt.replace(tzinfo=None)
            return dt

        # Normalize datetime objects
        start_date = to_naive(start_date)
        end_date = to_naive(end_date)

        if not sync_info:
            sync_info = SyncInfoModel(
                id="last_sync",
                last_sync_date=datetime.now(),
                start_date=start_date,
                end_date=end_date
            )
            db.add(sync_info)
        else:
            sync_info.last_sync_date = datetime.now()

            # Compare with normalized dates
            if start_date is not None:
                last_start = to_naive(sync_info.start_date)
                if last_start is None or start_date < last_start:
                    sync_info.start_date = start_date

            if end_date is not None:
                last_end = to_naive(sync_info.end_date)
                if last_end is None or end_date > last_end:
                    sync_info.end_date = end_date

        db.commit()
        db.refresh(sync_info)
        return sync_info
