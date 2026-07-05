import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.db.crud import SyncInfoCrud, TransactionCrud
from app.models.schemas import DateRange
from sync_fakes import make_email, make_service

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture()
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSession()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


RANGE = DateRange(
    start_date=datetime(2026, 6, 14), end_date=datetime(2026, 6, 16)
)


def test_force_sync_stores_and_marks_range(db_session):
    service = make_service(
        db_session,
        [[make_email("m1"), make_email("m2", merchant="PRICESMART")]],
    )
    result = asyncio.run(service.force_sync(RANGE))

    assert (result.fetched, result.stored, result.skipped, result.failed) == (2, 2, 0, 0)
    sync_info = SyncInfoCrud.get_last_sync(db_session)
    assert sync_info.start_date == RANGE.start_date
    assert sync_info.end_date == RANGE.end_date
    assert result.last_sync_date == sync_info.last_sync_date


def test_force_sync_refetches_synced_range_and_skips_stored(db_session):
    # Two batches: the second force_sync of the SAME range must still hit
    # Gmail (no gap detection) but skip the stored email before classifying.
    service = make_service(db_session, [[make_email("m1")], [make_email("m1")]])
    asyncio.run(service.force_sync(RANGE))
    result = asyncio.run(service.force_sync(RANGE))

    assert (result.fetched, result.stored, result.skipped, result.failed) == (1, 0, 1, 0)
    assert len(service.gmail_service.queries) == 2  # fetched twice, no gap short-circuit
    assert len(TransactionCrud.get_transactions(db_session)) == 1
    assert service.classifier.calls == ["HI-LO GROCERY"]  # skipped before classification


def test_force_sync_failure_leaves_range_unmarked(db_session):
    service = make_service(
        db_session,
        [[make_email("m1"), make_email("m2", parseable=False)]],
    )
    result = asyncio.run(service.force_sync(RANGE))

    assert (result.fetched, result.stored, result.skipped, result.failed) == (2, 1, 0, 1)
    assert SyncInfoCrud.get_last_sync(db_session) is None
    assert result.last_sync_date is None
