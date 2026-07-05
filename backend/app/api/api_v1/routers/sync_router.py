from fastapi import APIRouter, Depends, HTTPException

from app.api.api_v1.dependencies import get_transaction_service
from app.core.exceptions import GmailAPIError
from app.db.crud import SyncInfoCrud
from app.models.schemas import DateRange, SyncRequest, SyncResult, SyncStatus
from app.services.transaction_service import TransactionService

router = APIRouter()


@router.get("/sync/status", response_model=SyncStatus)
async def get_sync_status(
        service: TransactionService = Depends(get_transaction_service)
):
    """Report when data was last synced and the range sync covers."""
    sync_info = SyncInfoCrud.get_last_sync(service.db)
    if not sync_info:
        return SyncStatus()
    return SyncStatus(
        last_sync_date=sync_info.last_sync_date,
        synced_start_date=sync_info.start_date,
        synced_end_date=sync_info.end_date,
    )


@router.post("/sync", response_model=SyncResult)
async def trigger_sync(
        request: SyncRequest,
        service: TransactionService = Depends(get_transaction_service)
):
    """Force a re-fetch of the given date range from Gmail."""
    if request.start_date > request.end_date:
        raise HTTPException(status_code=400, detail="start_date must be before end_date")
    date_range = DateRange(start_date=request.start_date, end_date=request.end_date)
    try:
        return await service.force_sync(date_range)
    except GmailAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))
