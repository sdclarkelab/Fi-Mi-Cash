import asyncio
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.db.crud import SyncInfoCrud, TransactionCrud
from app.models.schemas import DateRange, EmailMessage, MerchantCategory
from app.services.transaction_service import TransactionService

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


RANGE = DateRange(
    start_date=datetime(2026, 6, 14), end_date=datetime(2026, 6, 16)
)


def make_service(db, batches):
    return TransactionService(
        gmail_service=FakeGmailService(batches),
        classifier=FakeClassifier(),
        db=db,
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
