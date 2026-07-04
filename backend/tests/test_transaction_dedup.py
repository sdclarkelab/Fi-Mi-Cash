import uuid
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base_class import Base
from app.db.crud import TransactionCrud
from app.models.schemas import Transaction

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


def make_transaction(
    message_id=None,
    merchant="COFFEE SPOT",
    amount="1500.00",
    date=datetime(2026, 6, 15, 12, 30),
):
    return Transaction(
        id=uuid.uuid4(),
        date=date,
        amount=Decimal(amount),
        merchant=merchant,
        primary_category="Food & Dining",
        subcategory="Coffee Shops",
        confidence=0.9,
        description="test",
        email_message_id=message_id,
        source="email" if message_id else "manual",
    )


def test_email_message_id_round_trips_through_create(db_session):
    row = TransactionCrud.create_transaction(db_session, make_transaction(message_id="msg-1"))
    assert row.email_message_id == "msg-1"


def test_duplicate_message_id_rejected_by_unique_index(db_session):
    TransactionCrud.create_transaction(db_session, make_transaction(message_id="msg-1"))
    with pytest.raises(IntegrityError):
        TransactionCrud.create_transaction(db_session, make_transaction(message_id="msg-1"))
    db_session.rollback()


def test_multiple_null_message_ids_allowed(db_session):
    TransactionCrud.create_transaction(db_session, make_transaction(message_id=None))
    TransactionCrud.create_transaction(db_session, make_transaction(message_id=None))
    # No IntegrityError: manual/legacy rows are outside the partial unique index
