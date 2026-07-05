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


def test_clean_gap_stores_all_and_marks_synced(db_session):
    service = make_service(
        db_session,
        [[make_email("m1"), make_email("m2", merchant="PRICESMART", amount="9,000.00")]],
    )
    asyncio.run(service._sync_transactions(RANGE))

    assert len(TransactionCrud.get_transactions(db_session)) == 2
    sync_info = SyncInfoCrud.get_last_sync(db_session)
    assert sync_info is not None
    assert sync_info.start_date == RANGE.start_date
    assert sync_info.end_date == RANGE.end_date


def test_two_identical_purchases_with_distinct_message_ids_both_store(db_session):
    # The Critical audit finding: same (date, amount, merchant), two emails.
    service = make_service(db_session, [[make_email("m1"), make_email("m2")]])
    asyncio.run(service._sync_transactions(RANGE))
    assert len(TransactionCrud.get_transactions(db_session)) == 2


def test_refetched_email_skipped_before_parse_and_classification(db_session):
    service = make_service(db_session, [[make_email("m1")]])
    asyncio.run(service._sync_transactions(RANGE))
    assert service.classifier.calls == ["HI-LO GROCERY"]

    # A wider request re-fetches the same email (sliding-window behavior)
    service.gmail_service.batches = [[make_email("m1")]]
    wider = DateRange(
        start_date=datetime(2026, 6, 10), end_date=datetime(2026, 6, 16)
    )
    asyncio.run(service._sync_transactions(wider))

    assert len(TransactionCrud.get_transactions(db_session)) == 1
    assert service.classifier.calls == ["HI-LO GROCERY"]  # not classified again


def test_failing_email_leaves_gap_unsynced_but_stores_siblings(db_session):
    service = make_service(
        db_session, [[make_email("m1"), make_email("m2", parseable=False)]]
    )
    asyncio.run(service._sync_transactions(RANGE))

    assert len(TransactionCrud.get_transactions(db_session)) == 1
    assert SyncInfoCrud.get_last_sync(db_session) is None  # gap NOT marked synced


def test_retry_after_failure_only_reparses_failed_email(db_session):
    service = make_service(
        db_session, [[make_email("m1"), make_email("m2", parseable=False)]]
    )
    asyncio.run(service._sync_transactions(RANGE))
    assert SyncInfoCrud.get_last_sync(db_session) is None

    # Next request retries the same (still-unsynced) range; the email now parses
    service.gmail_service.batches = [
        [make_email("m1"), make_email("m2", merchant="PHARMACY PLUS")]
    ]
    asyncio.run(service._sync_transactions(RANGE))

    assert len(TransactionCrud.get_transactions(db_session)) == 2
    assert SyncInfoCrud.get_last_sync(db_session) is not None
    # m1 classified once on first pass, m2 once on retry — no re-classification
    assert service.classifier.calls == ["HI-LO GROCERY", "PHARMACY PLUS"]


def test_mixed_gaps_marks_only_the_clean_one(db_session):
    # Existing synced range 6/14..6/16; request 6/10..6/20 → two gaps:
    # before (6/10..6/14, will fail) and after (6/16..6/20, clean).
    SyncInfoCrud.update_last_sync(
        db_session, datetime(2026, 6, 14), datetime(2026, 6, 16)
    )
    before_gap = [make_email("m1", date=datetime(2026, 6, 12, 10, 0), parseable=False)]
    after_gap = [make_email("m2", date=datetime(2026, 6, 18, 10, 0))]
    service = make_service(db_session, [before_gap, after_gap])

    requested = DateRange(
        start_date=datetime(2026, 6, 10), end_date=datetime(2026, 6, 20)
    )
    asyncio.run(service._sync_transactions(requested))

    sync_info = SyncInfoCrud.get_last_sync(db_session)
    # Failing "before" gap stays unsynced (start unchanged); clean "after"
    # gap extends the end.
    assert sync_info.start_date == datetime(2026, 6, 14)
    assert sync_info.end_date == datetime(2026, 6, 20)
    assert len(TransactionCrud.get_transactions(db_session)) == 1


def test_concurrent_sync_duplicate_insert_is_swallowed(db_session, monkeypatch):
    # First sync stores "m1" normally.
    service = make_service(db_session, [[make_email("m1")]])
    asyncio.run(service._sync_transactions(RANGE))
    assert len(TransactionCrud.get_transactions(db_session)) == 1

    # Simulate a second, overlapping/concurrent sync whose dedup pre-checks
    # both miss (e.g. raced against another session that stored "m1" between
    # the check and the insert) and whose Gmail fetch returns "m1" again.
    monkeypatch.setattr(
        TransactionCrud, "transaction_exists_by_message_id",
        staticmethod(lambda db, mid: False),
    )
    monkeypatch.setattr(
        TransactionCrud, "transaction_exists",
        staticmethod(lambda db, transaction: False),
    )

    wider = DateRange(
        start_date=datetime(2026, 6, 10), end_date=datetime(2026, 6, 20)
    )
    service.gmail_service.batches = [[make_email("m1")]]

    # Must not raise IntegrityError out of _sync_transactions.
    asyncio.run(service._sync_transactions(wider))

    # Still exactly one row for "m1" — duplicate insert was rejected by the
    # unique partial index and swallowed, not double-stored.
    rows = TransactionCrud.get_transactions(db_session)
    assert len(rows) == 1
    assert rows[0].email_message_id == "m1"

    # The gap was otherwise clean, so it should still be marked synced.
    sync_info = SyncInfoCrud.get_last_sync(db_session)
    assert sync_info.start_date == datetime(2026, 6, 10)
    assert sync_info.end_date == datetime(2026, 6, 20)
