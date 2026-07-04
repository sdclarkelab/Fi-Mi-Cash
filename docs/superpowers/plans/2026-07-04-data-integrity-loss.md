# Data-Integrity Loss Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the two silent-data-loss paths in Gmail sync: dedup that drops legitimate same-day duplicate purchases, and parse failures that are dropped while their range is marked synced.

**Architecture:** Carry the Gmail message ID (already fetched, currently discarded) end-to-end into a new nullable `transactions.email_message_id` column with a unique partial index; dedup on it *before* parsing/classification, keeping the old `(date, amount, merchant)` check only for legacy NULL-ID rows. Rework `_sync_transactions` to per-gap accounting: a gap is marked synced only when every email in it parsed; a failed gap stays unsynced and is retried cheaply on the next request. A tiny idempotent startup migration adds the column/index to the existing SQLite DB (no alembic in this project).

**Tech Stack:** FastAPI, SQLAlchemy 2 (declarative), SQLite, Pydantic v2, pytest (no pytest-asyncio — use `asyncio.run(...)` in tests).

**Spec:** `docs/superpowers/specs/2026-07-04-data-integrity-loss-design.md`

## Global Constraints

- Work on branch `fix/data-integrity-loss` off local `main`.
- Backend tests run as: `cd backend && .venv/bin/python -m pytest tests -v`.
- The pre-commit hook blocks secret files and runs gitleaks; never `git add -f`.
- The live `backend/app/transactions.db` holds real data — never modify or delete it; tests use in-memory or `tmp_path` SQLite only.
- `Base` is `app.db.base_class.Base` (the one in `app/db/database.py` is dead — don't import it in new code).
- End every commit message with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Carry the Gmail message ID into `EmailMessage`

**Files:**
- Modify: `backend/app/models/schemas.py:9-13` (`EmailMessage`)
- Modify: `backend/app/services/gmail_service.py:81-105` (`_fetch_email_message`)
- Test: `backend/tests/test_gmail_service.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `EmailMessage.message_id: str` (required field) — Task 5 reads it for pre-parse dedup; every `EmailMessage(...)` construction anywhere must now pass `message_id`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_gmail_service.py`:

```python
import base64
from unittest.mock import MagicMock

from app.services.gmail_service import GmailService


def _fake_gmail_api():
    service = MagicMock()
    service.users().messages().get().execute.return_value = {
        "internalDate": "1750000000000",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Transaction Approved"},
                {"name": "From", "value": "no-reply-ncbcardalerts@jncb.com"},
            ],
            "body": {"data": base64.urlsafe_b64encode(b"hello").decode()},
        },
    }
    return service


def test_fetch_email_message_carries_gmail_message_id():
    gs = GmailService()
    gs._service = _fake_gmail_api()
    email = gs._fetch_email_message("abc123")
    assert email.message_id == "abc123"
    assert email.body == "hello"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && .venv/bin/python -m pytest tests/test_gmail_service.py -v`
Expected: FAIL — `AttributeError: 'EmailMessage' object has no attribute 'message_id'` (Pydantic v2 models raise `AttributeError` for unknown attributes; the model constructs fine because extra kwargs are ignored by default).

- [ ] **Step 3: Add `message_id` to `EmailMessage` and populate it**

In `backend/app/models/schemas.py`, change `EmailMessage` to:

```python
class EmailMessage(BaseModel):
    message_id: str
    subject: str
    sender: str
    date: datetime
    body: str
```

In `backend/app/services/gmail_service.py`, in `_fetch_email_message`, change the return to:

```python
            return EmailMessage(
                message_id=message_id,
                subject=headers.get('subject', ''),
                sender=headers.get('from', ''),
                date=datetime.fromtimestamp(int(msg['internalDate']) / 1000),
                body=body
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS (new test + existing 10).

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_gmail_service.py backend/app/models/schemas.py backend/app/services/gmail_service.py
git commit -m "feat: carry Gmail message id on EmailMessage

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `email_message_id` column, unique partial index, and plumbing

**Files:**
- Modify: `backend/app/models/transaction_model.py`
- Modify: `backend/app/models/schemas.py` (`Transaction`)
- Modify: `backend/app/db/crud.py:18-40` (`create_transaction`)
- Modify: `backend/app/services/transaction_service.py:231-246` (`_parse_transaction` return) and `:317-336` (`_to_transaction`)
- Test: `backend/tests/test_transaction_dedup.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks (independent of Task 1).
- Produces: `TransactionModel.email_message_id` column (nullable String, unique partial index named `ix_transactions_email_message_id`); `Transaction.email_message_id: Optional[str] = None`; `TransactionCrud.create_transaction` persists it. Tasks 3–5 rely on these exact names.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_transaction_dedup.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_transaction_dedup.py -v`
Expected: Pydantic v2 silently ignores the unknown `email_message_id` kwarg, so construction succeeds; `test_email_message_id_round_trips_through_create` FAILS with `AttributeError` on the model row, `test_duplicate_message_id_rejected_by_unique_index` FAILS with `DID NOT RAISE`, and `test_multiple_null_message_ids_allowed` passes trivially.

- [ ] **Step 3: Add the column, index, schema field, and plumbing**

`backend/app/models/transaction_model.py` — add `Index` to the import and the column + table args at the end of the class:

```python
import uuid

from sqlalchemy import Column, String, DateTime, Numeric, Float, Boolean, Date, Index

from app.db.base_class import Base


class TransactionModel(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    date = Column(DateTime, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    merchant = Column(String, index=True)
    primary_category = Column(String, index=True)
    subcategory = Column(String, index=True)
    confidence = Column(Float)
    description = Column(String)
    excluded = Column(Boolean, default=False, nullable=False)

    # Exchange rate fields for USD transactions
    original_currency = Column(String(3))  # USD, JMD, etc.
    original_amount = Column(Numeric(10, 2))  # Amount in original currency
    exchange_rate = Column(Numeric(10, 6))  # Exchange rate applied
    exchange_rate_date = Column(Date)  # Date the exchange rate was from

    # Card information
    card_type = Column(String(50))  # Card type used for transaction

    # Source information
    source = Column(String(20), default="email", nullable=False)  # "email" or "manual"

    # Gmail message id for email-synced rows; NULL for manual and pre-migration rows
    email_message_id = Column(String)

    __table_args__ = (
        Index(
            "ix_transactions_email_message_id",
            "email_message_id",
            unique=True,
            sqlite_where=email_message_id.isnot(None),
        ),
    )
```

`backend/app/models/schemas.py` — in `Transaction`, after the `source` field add:

```python
    # Gmail message id for email-synced transactions (dedup key); None for manual entries
    email_message_id: Optional[str] = None
```

`backend/app/db/crud.py` — in `create_transaction`, after the `source=...` line add:

```python
            source=getattr(transaction, 'source', 'email'),
            email_message_id=transaction.email_message_id
```

`backend/app/services/transaction_service.py` — in `_parse_transaction`'s `return Transaction(...)`, after `source="email"` add:

```python
                source="email",
                email_message_id=email.message_id
```

and in `_to_transaction`, after `source=tx.source or "email"` add:

```python
            source=tx.source or "email",
            email_message_id=tx.email_message_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_transaction_dedup.py backend/app/models/transaction_model.py backend/app/models/schemas.py backend/app/db/crud.py backend/app/services/transaction_service.py
git commit -m "feat: store Gmail message id on transactions with unique partial index

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Dedup queries — message-id check plus legacy-only fallback

**Files:**
- Modify: `backend/app/db/crud.py:108-114` (`transaction_exists`, and new method next to it)
- Test: `backend/tests/test_transaction_dedup.py` (extend)

**Interfaces:**
- Consumes: `TransactionModel.email_message_id`, `make_transaction` helper from Task 2's test file.
- Produces: `TransactionCrud.transaction_exists_by_message_id(db: Session, message_id: str) -> bool`; `TransactionCrud.transaction_exists(db, transaction) -> bool` now matches **only rows whose `email_message_id` IS NULL**. Task 5 calls both.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_transaction_dedup.py`:

```python
def test_transaction_exists_by_message_id(db_session):
    TransactionCrud.create_transaction(db_session, make_transaction(message_id="msg-1"))
    assert TransactionCrud.transaction_exists_by_message_id(db_session, "msg-1") is True
    assert TransactionCrud.transaction_exists_by_message_id(db_session, "msg-2") is False


def test_legacy_fallback_ignores_rows_that_have_a_message_id(db_session):
    # The Critical audit finding: a second same-day identical purchase arrives
    # as a distinct email. The stored row has a message id, so the legacy
    # (date, amount, merchant) check must NOT match it.
    TransactionCrud.create_transaction(db_session, make_transaction(message_id="msg-1"))
    second_purchase = make_transaction(message_id="msg-2")
    assert TransactionCrud.transaction_exists(db_session, second_purchase) is False


def test_legacy_fallback_matches_pre_migration_rows(db_session):
    # A pre-migration row (NULL message id) re-fetched by a sliding-window
    # re-sync must still dedup on (date, amount, merchant).
    TransactionCrud.create_transaction(db_session, make_transaction(message_id=None))
    refetched = make_transaction(message_id="msg-9")
    assert TransactionCrud.transaction_exists(db_session, refetched) is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_transaction_dedup.py -v`
Expected: `test_transaction_exists_by_message_id` FAILS with `AttributeError: ... has no attribute 'transaction_exists_by_message_id'`; `test_legacy_fallback_ignores_rows_that_have_a_message_id` FAILS (`transaction_exists` still matches everything); `test_legacy_fallback_matches_pre_migration_rows` PASSES (documents preserved behavior).

- [ ] **Step 3: Implement both checks**

In `backend/app/db/crud.py`, replace `transaction_exists` with:

```python
    @staticmethod
    def transaction_exists_by_message_id(db: Session, message_id: str) -> bool:
        return db.query(TransactionModel).filter(
            TransactionModel.email_message_id == message_id
        ).first() is not None

    @staticmethod
    def transaction_exists(db: Session, transaction: Transaction) -> bool:
        """Legacy dedup for rows synced before email_message_id existed.

        Restricted to NULL-message-id rows so two distinct emails with
        identical (date, amount, merchant) both store.
        """
        return db.query(TransactionModel).filter(
            TransactionModel.email_message_id.is_(None),
            TransactionModel.date == transaction.date,
            TransactionModel.amount == transaction.amount,
            TransactionModel.merchant == transaction.merchant
        ).first() is not None
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_transaction_dedup.py backend/app/db/crud.py
git commit -m "fix: dedup on Gmail message id; legacy triple-key check only for NULL-id rows

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Idempotent startup migration for the existing DB

**Files:**
- Create: `backend/app/db/migrations.py`
- Modify: `backend/app/main.py:17-29` (lifespan)
- Modify: `CLAUDE.md` (the "no alembic migrations" sentence)
- Test: `backend/tests/test_migrations.py` (create)

**Interfaces:**
- Consumes: nothing from other tasks (the column name/index name must match Task 2: `email_message_id`, `ix_transactions_email_message_id`).
- Produces: `run_startup_migrations(engine) -> None` in `app.db.migrations`, called from `main.py` lifespan after `create_all`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_migrations.py`:

```python
import pytest
from sqlalchemy import create_engine, inspect, text

from app.db.migrations import run_startup_migrations


def _legacy_engine(tmp_path):
    """A transactions table as it exists in the live pre-migration DB."""
    engine = create_engine(f"sqlite:///{tmp_path}/legacy.db")
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE transactions ("
            "id VARCHAR(36) PRIMARY KEY, date DATETIME, amount NUMERIC(10,2) NOT NULL, "
            "merchant VARCHAR, primary_category VARCHAR, subcategory VARCHAR, "
            "confidence FLOAT, description VARCHAR, excluded BOOLEAN NOT NULL, "
            "original_currency VARCHAR(3), original_amount NUMERIC(10,2), "
            "exchange_rate NUMERIC(10,6), exchange_rate_date DATE, "
            "card_type VARCHAR(50), source VARCHAR(20) NOT NULL)"
        ))
        conn.execute(text(
            "INSERT INTO transactions (id, date, amount, merchant, primary_category, "
            "subcategory, confidence, description, excluded, source) "
            "VALUES ('t1', '2026-06-15 12:30:00', 1500, 'COFFEE SPOT', 'Food & Dining', "
            "'Coffee Shops', 0.9, 'test', 0, 'email')"
        ))
    return engine


def test_migration_adds_column_and_index(tmp_path):
    engine = _legacy_engine(tmp_path)
    run_startup_migrations(engine)

    columns = {c["name"] for c in inspect(engine).get_columns("transactions")}
    assert "email_message_id" in columns
    with engine.connect() as conn:
        # SQLAlchemy's SQLite inspector does not reliably reflect partial
        # indexes — check sqlite_master directly.
        index = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND name='ix_transactions_email_message_id'"
        )).scalar()
        value = conn.execute(
            text("SELECT email_message_id FROM transactions WHERE id='t1'")
        ).scalar()
    assert index == "ix_transactions_email_message_id"
    assert value is None  # existing rows stay, with NULL message id

    # The migrated index enforces uniqueness of non-NULL message ids
    with pytest.raises(Exception):
        with engine.begin() as conn:
            conn.execute(text(
                "UPDATE transactions SET email_message_id='dup' WHERE id='t1'"
            ))
            conn.execute(text(
                "INSERT INTO transactions (id, date, amount, excluded, source, email_message_id) "
                "VALUES ('t2', '2026-06-16 10:00:00', 900, 0, 'email', 'dup')"
            ))


def test_migration_is_idempotent(tmp_path):
    engine = _legacy_engine(tmp_path)
    run_startup_migrations(engine)
    run_startup_migrations(engine)  # second run must not raise

    columns = [c["name"] for c in inspect(engine).get_columns("transactions")]
    assert columns.count("email_message_id") == 1


def test_migration_noop_without_transactions_table(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path}/empty.db")
    run_startup_migrations(engine)  # fresh DB before create_all: must not raise
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_migrations.py -v`
Expected: FAIL at import — `ModuleNotFoundError: No module named 'app.db.migrations'`.

- [ ] **Step 3: Implement the migration and wire it into startup**

Create `backend/app/db/migrations.py`:

```python
from sqlalchemy import inspect, text

from app.core.logger import logger


def run_startup_migrations(engine) -> None:
    """Idempotent, additive schema fixes that create_all() can't apply to
    already-existing tables (this project has no alembic)."""
    inspector = inspect(engine)
    if "transactions" not in inspector.get_table_names():
        return  # fresh DB: create_all() builds the full schema

    columns = {col["name"] for col in inspector.get_columns("transactions")}
    with engine.begin() as conn:
        if "email_message_id" not in columns:
            logger.info("Migrating: adding transactions.email_message_id")
            conn.execute(text(
                "ALTER TABLE transactions ADD COLUMN email_message_id VARCHAR"
            ))
        conn.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_email_message_id "
            "ON transactions(email_message_id) WHERE email_message_id IS NOT NULL"
        ))
```

In `backend/app/main.py`, add the import and call it in the lifespan right after `create_all`:

```python
from app.db.database import engine
from app.db.migrations import run_startup_migrations
```

```python
    # Initialize database tables
    logger.info("Creating database tables if they don't exist")
    Base.metadata.create_all(bind=engine)
    run_startup_migrations(engine)
```

In `CLAUDE.md`, update the sentence in the backend commands section:

Replace:
> There are no alembic migrations (despite what README.md says — tables are created via `Base.metadata.create_all()` at startup) and no configured linter.

With:
> There are no alembic migrations (despite what README.md says — tables are created via `Base.metadata.create_all()` at startup, followed by the small additive migrations in `backend/app/db/migrations.py`) and no configured linter.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_migrations.py backend/app/db/migrations.py backend/app/main.py CLAUDE.md
git commit -m "feat: startup migration adds email_message_id to existing DBs

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Per-gap sync — pre-parse dedup, failures keep the gap unsynced

**Files:**
- Modify: `backend/app/services/transaction_service.py:59-79` (`_sync_transactions`)
- Test: `backend/tests/test_sync_integrity.py` (create)

**Interfaces:**
- Consumes: `EmailMessage.message_id` (Task 1), `TransactionCrud.transaction_exists_by_message_id` / restricted `transaction_exists` (Task 3), `Transaction.email_message_id` plumbing (Task 2).
- Produces: new `_sync_transactions` behavior — per-gap `SyncInfoCrud.update_last_sync(gap.start_date, gap.end_date)` only on zero-failure gaps. No signature changes.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sync_integrity.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify the new behaviors fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_sync_integrity.py -v`
Expected: `test_failing_email_leaves_gap_unsynced_but_stores_siblings`, `test_retry_after_failure_only_reparses_failed_email`, `test_refetched_email_skipped_before_parse_and_classification`, and `test_mixed_gaps_marks_only_the_clean_one` FAIL (old code marks everything synced and classifies before dedup). The first two tests may already PASS (dedup fixed in Task 3) — that's fine.

- [ ] **Step 3: Rework `_sync_transactions`**

In `backend/app/services/transaction_service.py`, replace `_sync_transactions` with:

```python
    async def _sync_transactions(self, date_range: DateRange):
        """Fetch transactions from Gmail and store in SQLite if not already present.

        Each gap is marked synced only if every email in it parsed and stored;
        a gap with failures stays unsynced so the next request retries it
        (already-stored emails are skipped by message id, so retries are cheap).
        """
        sync_gaps = SyncInfoCrud.get_sync_gaps(self.db, date_range)

        for gap in sync_gaps:
            query = self._build_gmail_query(gap)
            emails = self.gmail_service.get_messages(query)

            failed_dates = []
            for email in emails:
                if TransactionCrud.transaction_exists_by_message_id(self.db, email.message_id):
                    continue

                try:
                    transaction = await self._parse_transaction(email)
                except Exception as e:
                    logger.error(f"Unexpected error processing email dated {email.date}: {e}")
                    transaction = None

                if transaction is None:
                    failed_dates.append(email.date)
                    continue

                # Legacy fallback: rows synced before email_message_id existed
                if not TransactionCrud.transaction_exists(self.db, transaction):
                    TransactionCrud.create_transaction(self.db, transaction)

            if failed_dates:
                logger.error(
                    f"{len(failed_dates)} email(s) failed to parse in sync range "
                    f"{gap.start_date}..{gap.end_date} (email dates: {failed_dates}); "
                    f"range left unsynced and will be retried on the next request"
                )
            else:
                SyncInfoCrud.update_last_sync(self.db, gap.start_date, gap.end_date)
```

(The old early-return for empty `sync_gaps` and the trailing whole-range `update_last_sync` call are gone — marking is per-gap now.)

- [ ] **Step 4: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/tests/test_sync_integrity.py backend/app/services/transaction_service.py
git commit -m "fix: dedup before parse; parse failures keep their sync gap unsynced

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: End-to-end verification against a real server

**Files:**
- No source changes expected; scratch files only (use the session scratchpad, not the repo).

**Interfaces:**
- Consumes: everything above.
- Produces: verified evidence that startup migration + sync integrity work on a real (scratch) server.

- [ ] **Step 1: Verify the startup migration on a copy of a legacy DB**

From a scratch directory (never the real `backend/app/` CWD, and never the real `transactions.db`):

1. Create a scratch CWD with a `.env` containing `API_KEY=e2e-test-key`, `OPENAI_API_KEY=dummy`, `GMAIL_CREDENTIALS_PATH=credentials.json` (file need not exist — Gmail is lazily initialized and this test never triggers a sync).
2. Build a legacy-schema `transactions.db` in that scratch CWD using the same `CREATE TABLE`/`INSERT` SQL as `tests/test_migrations.py::_legacy_engine` (via `sqlite3` CLI or a short Python snippet).
3. Start the server from the scratch CWD: `cd <scratch> && <repo>/backend/.venv/bin/python -m uvicorn app.main:app --port 8099 --app-dir <repo>/backend`.
4. Check the log shows `Migrating: adding transactions.email_message_id`, then
   `sqlite3 transactions.db "PRAGMA table_info(transactions)"` shows the new column and `sqlite3 transactions.db "PRAGMA index_list(transactions)"` shows `ix_transactions_email_message_id`, and the seeded row survived (`SELECT count(*) FROM transactions` → 1).
5. Restart the server once — no migration log line the second time, no error (idempotence).
6. `curl -s -H "X-API-Key: e2e-test-key" "http://127.0.0.1:8099/api/v1/transactions/count?start_date=2026-06-01T00:00:00&end_date=2026-06-30T23:59:59"` — hits the DB read path end-to-end. A Gmail-related error is acceptable only if it proves the request got past auth and into the service; a clean count response (the range may sync-check first) is the goal — if Gmail init blocks the read, verify the read path instead with `sqlite3` and note it.
7. Stop the server.

- [ ] **Step 2: Run the full test suites one final time**

Run: `cd backend && .venv/bin/python -m pytest tests -v` — expected: all PASS.
Run: `cd frontend && CI=true npm test -- --watchAll=false` — expected: same as before this branch (3 suites pass; `App.test.js` fails from the pre-existing axios-ESM Jest issue, tracked in `.superpowers/sdd/progress.md`).

- [ ] **Step 3: Clean up scratch files**

Remove the scratch CWD (it contains only dummy keys and a synthetic DB).

---

## Self-review notes

- Spec coverage: §1 dedup → Tasks 1–3; §2 migration → Task 4; §3 per-gap sync → Task 5; testing section → each task's tests + Task 6.
- Type consistency: `message_id: str` on `EmailMessage` (Tasks 1, 5); `email_message_id` column/field (Tasks 2–5); index name `ix_transactions_email_message_id` identical in model (Task 2) and migration SQL (Task 4); `transaction_exists_by_message_id(db, message_id)` defined in Task 3, called in Task 5.
- The `test_update_transaction_category.py` fixtures build `TransactionModel` directly without `email_message_id` — the column is nullable, so they keep passing unchanged.
