import uuid
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.schemas import Transaction, DateRange
from app.models.sync_info_model import SyncInfoModel
from app.models.transaction_model import TransactionModel

settings = get_settings()


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
            
            # Use intelligent range management instead of always expanding
            new_start, new_end = SyncInfoCrud._calculate_optimal_sync_range(
                sync_info, start_date, end_date
            )
            
            sync_info.start_date = new_start
            sync_info.end_date = new_end

        db.commit()
        db.refresh(sync_info)
        return sync_info

    @staticmethod
    def _calculate_optimal_sync_range(
        sync_info: SyncInfoModel, 
        requested_start: Optional[datetime], 
        requested_end: Optional[datetime]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """
        Calculate optimal sync range using sliding window strategy with configurable limits
        """
        def to_naive(dt):
            if dt and dt.tzinfo:
                return dt.replace(tzinfo=None)
            return dt

        # Get current sync range
        current_start = to_naive(sync_info.start_date)
        current_end = to_naive(sync_info.end_date)
        
        # Normalize requested dates
        requested_start = to_naive(requested_start)
        requested_end = to_naive(requested_end)
        
        # If no current range, use requested range (with limits)
        if not current_start or not current_end:
            return SyncInfoCrud._apply_sync_limits(requested_start, requested_end)
        
        # Calculate the union of current and requested ranges
        union_start = min(filter(None, [current_start, requested_start]))
        union_end = max(filter(None, [current_end, requested_end]))
        
        # Check if the union exceeds maximum allowed days
        max_range_days = timedelta(days=settings.MAX_SYNC_DAYS)
        if union_end - union_start > max_range_days:
            # Use sliding window: prioritize recent data
            if requested_end:
                # Keep requested end, limit start date
                optimal_start = max(
                    union_start,
                    requested_end - max_range_days
                )
                optimal_end = requested_end
            else:
                # Keep current end, limit start date  
                optimal_start = max(
                    union_start,
                    current_end - max_range_days
                )
                optimal_end = current_end
        else:
            # Union fits within limits, check for minimal expansion
            overlap_threshold = timedelta(hours=settings.MIN_SYNC_OVERLAP_HOURS)
            
            # Only expand if there's minimal overlap with existing range
            if requested_start and current_start:
                start_gap = abs(requested_start - current_start)
                if start_gap < overlap_threshold:
                    union_start = current_start  # Don't expand for minimal difference
                    
            if requested_end and current_end:
                end_gap = abs(requested_end - current_end)
                if end_gap < overlap_threshold:
                    union_end = current_end  # Don't expand for minimal difference
                    
            optimal_start = union_start
            optimal_end = union_end
        
        return optimal_start, optimal_end

    @staticmethod
    def _apply_sync_limits(
        start_date: Optional[datetime], 
        end_date: Optional[datetime]
    ) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Apply maximum sync limits to a date range"""
        if not start_date or not end_date:
            return start_date, end_date
            
        max_range_days = timedelta(days=settings.MAX_SYNC_DAYS)
        
        # If range exceeds maximum, truncate from the start (keep recent data)
        if end_date - start_date > max_range_days:
            start_date = end_date - max_range_days
            
        return start_date, end_date

    @staticmethod
    def get_sync_gaps(db: Session, requested_range: DateRange) -> List[DateRange]:
        """
        Identify date ranges that need syncing by finding gaps in current sync coverage
        """
        sync_info = SyncInfoCrud.get_last_sync(db)
        
        if not sync_info or not sync_info.start_date or not sync_info.end_date:
            # No previous sync, return the requested range (with limits applied)
            limited_start, limited_end = SyncInfoCrud._apply_sync_limits(
                requested_range.start_date, requested_range.end_date
            )
            return [DateRange(start_date=limited_start, end_date=limited_end)]
        
        def to_naive(dt):
            if dt and dt.tzinfo:
                return dt.replace(tzinfo=None)
            return dt
        
        # Normalize dates
        sync_start = to_naive(sync_info.start_date)
        sync_end = to_naive(sync_info.end_date) 
        req_start = to_naive(requested_range.start_date)
        req_end = to_naive(requested_range.end_date)
        
        gaps = []
        
        # Check for gap before current sync range
        if req_start < sync_start:
            gap_end = min(sync_start, req_end)
            limited_start, limited_end = SyncInfoCrud._apply_sync_limits(req_start, gap_end)
            gaps.append(DateRange(start_date=limited_start, end_date=limited_end))
        
        # Check for gap after current sync range
        if req_end > sync_end:
            gap_start = max(sync_end, req_start)
            limited_start, limited_end = SyncInfoCrud._apply_sync_limits(gap_start, req_end)
            gaps.append(DateRange(start_date=limited_start, end_date=limited_end))
        
        return gaps
