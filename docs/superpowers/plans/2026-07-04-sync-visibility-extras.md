# Sync Visibility + Extras Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sync status + manual force-sync ("Sync now"), finish the top-spending-category card, and client-side CSV export of the current filtered view.

**Architecture:** Extract the per-email ingest loop from `_sync_transactions` into a shared `_process_emails` helper; build `force_sync` on it (re-fetches a range from Gmail ignoring `sync_info`; message-id dedup makes that safe) exposed via a new `sync_router` (`GET /sync/status`, `POST /sync`). Frontend gets a `SyncControl` in the toolbar, the already-committed `TopSpendingCategory` card gets its missing backend fields and gets wired into `App.jsx`, and CSV export is a pure client-side helper + button fed by the existing `GET /transactions`.

**Tech Stack:** FastAPI, SQLAlchemy/SQLite, Pydantic v2, pytest (`asyncio.run`, no pytest-asyncio); React 18 + CRA, React Query, axios, Jest/@testing-library.

**Spec:** `docs/superpowers/specs/2026-07-04-sync-visibility-extras-design.md`

## Global Constraints

- Work on branch `feat/sync-visibility-extras` off local `main`.
- Backend tests: `cd backend && .venv/bin/python -m pytest tests -v`. Frontend tests: `cd frontend && CI=true npm test -- --watchAll=false` (the pre-existing `App.test.js` axios-ESM failure is expected and out of scope).
- The live `backend/app/transactions.db`, `.env`, `credentials.json`, `token.json` hold real data/secrets — never touch them; tests use in-memory SQLite and mocks only. Never `git add -f`; the pre-commit hook runs gitleaks.
- Lazy-sync behavior from roadmap item 3 must not change: a gap with any parse failure is NOT marked synced; message-id dedup runs BEFORE parse/classification; duplicate-insert `IntegrityError` is swallowed with rollback.
- Do NOT fix the pre-existing `average_transaction` denominator bug in `get_summary` (that is roadmap item 4) — leave that line exactly as found.
- New endpoints live under the existing `verify_api_key` guard; endpoint tests send header `X-API-Key: test-api-key` (set by `tests/conftest.py`).
- Backend test imports like `from sync_fakes import ...` work because pytest adds `backend/tests/` to `sys.path` (no `__init__.py` there — do not add one).
- End every commit message with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: Extract `_process_emails` and share the test fakes

**Files:**
- Modify: `backend/app/services/transaction_service.py:60-104` (`_sync_transactions`)
- Create: `backend/tests/sync_fakes.py`
- Modify: `backend/tests/test_sync_integrity.py` (replace in-file fakes with imports)

**Interfaces:**
- Consumes: current `_sync_transactions` (item 3 shape), current `test_sync_integrity.py` fakes.
- Produces: `async def _process_emails(self, emails) -> tuple[int, int, list]` returning `(stored, skipped, failed_dates)` — Task 2's `force_sync` calls it. `backend/tests/sync_fakes.py` exporting `FakeGmailService(batches)`, `FakeClassifier`, `make_email(message_id, merchant=..., amount=..., date=..., parseable=...)`, `make_service(db, batches)` — Tasks 2 and 3 import these.

This is a behavior-preserving refactor: the existing 27 backend tests are the net; no new tests.

- [ ] **Step 1: Confirm the suite is green before touching anything**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 27 passed.

- [ ] **Step 2: Create the shared fakes module**

Create `backend/tests/sync_fakes.py` by MOVING the fakes out of `test_sync_integrity.py` (delete `FakeGmailService`, `FakeClassifier`, `make_email`, and `make_service` from the test file — `RANGE` and the fixtures stay there):

```python
"""Shared fakes for sync-path tests. Only the Gmail and classifier
boundaries are faked — the service, parsing regexes, and DB code under
test stay real."""
from datetime import datetime

from app.models.schemas import EmailMessage, MerchantCategory
from app.services.transaction_service import TransactionService


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


def make_service(db, batches):
    return TransactionService(
        gmail_service=FakeGmailService(batches),
        classifier=FakeClassifier(),
        db=db,
    )
```

In `backend/tests/test_sync_integrity.py`, add at the top (with the other imports) and remove the now-moved definitions:

```python
from sync_fakes import make_email, make_service
```

Keep everything else in the test file unchanged (fixtures, `RANGE`, all test functions — they only use `make_email`, `make_service`, and attribute access like `service.gmail_service.batches` / `service.classifier.calls`, which still work). Remove imports the file no longer needs (`EmailMessage`, `MerchantCategory`, `TransactionService`) if nothing else in the file uses them.

- [ ] **Step 3: Run the suite to confirm the move is clean**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 27 passed.

- [ ] **Step 4: Extract `_process_emails` in the service**

In `backend/app/services/transaction_service.py`, replace the whole `_sync_transactions` method (currently lines 60–104) with:

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

            _, _, failed_dates = await self._process_emails(emails)

            if failed_dates:
                logger.error(
                    f"{len(failed_dates)} email(s) failed to parse in sync range "
                    f"{gap.start_date}..{gap.end_date} (email dates: {failed_dates}); "
                    f"range left unsynced and will be retried on the next request"
                )
            else:
                SyncInfoCrud.update_last_sync(self.db, gap.start_date, gap.end_date)

    async def _process_emails(self, emails) -> tuple:
        """Shared per-email ingest pipeline for lazy and forced syncs.

        Returns (stored, skipped, failed_dates). Skipped counts emails already
        stored — matched by message id, by a legacy pre-migration row, or by
        losing a duplicate-insert race to a concurrent sync.
        """
        stored = 0
        skipped = 0
        failed_dates = []
        for email in emails:
            if TransactionCrud.transaction_exists_by_message_id(self.db, email.message_id):
                skipped += 1
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
            if TransactionCrud.transaction_exists(self.db, transaction):
                skipped += 1
                continue

            try:
                TransactionCrud.create_transaction(self.db, transaction)
                stored += 1
            except IntegrityError:
                # A concurrent sync stored this email between our dedup
                # check and the insert — already stored, move on.
                self.db.rollback()
                skipped += 1
        return stored, skipped, failed_dates
```

(The `IntegrityError` import already exists from item 3. Note the only behavior-visible difference is counting, which nothing consumed before.)

- [ ] **Step 5: Run the full suite**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 27 passed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/services/transaction_service.py backend/tests/sync_fakes.py backend/tests/test_sync_integrity.py
git commit -m "refactor: extract shared _process_emails pipeline and test fakes

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `force_sync` service method + sync schemas

**Files:**
- Modify: `backend/app/models/schemas.py` (append three schemas)
- Modify: `backend/app/services/transaction_service.py` (new method + import)
- Test: `backend/tests/test_force_sync.py` (create)

**Interfaces:**
- Consumes: `_process_emails` and `sync_fakes` from Task 1.
- Produces: schemas `SyncStatus {last_sync_date, synced_start_date, synced_end_date: Optional[datetime]}`, `SyncRequest {start_date, end_date: datetime}`, `SyncResult {fetched, stored, skipped, failed: int, last_sync_date: Optional[datetime]}`; `async def force_sync(self, date_range: DateRange) -> SyncResult` on `TransactionService`. Task 3's router uses all four.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_force_sync.py`:

```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_force_sync.py -v`
Expected: FAIL — `AttributeError: 'TransactionService' object has no attribute 'force_sync'`.

- [ ] **Step 3: Add the schemas and the method**

Append to `backend/app/models/schemas.py`:

```python
class SyncStatus(BaseModel):
    last_sync_date: Optional[datetime] = None
    synced_start_date: Optional[datetime] = None
    synced_end_date: Optional[datetime] = None


class SyncRequest(BaseModel):
    start_date: datetime
    end_date: datetime


class SyncResult(BaseModel):
    fetched: int
    stored: int
    skipped: int
    failed: int
    last_sync_date: Optional[datetime] = None
```

In `backend/app/services/transaction_service.py`, extend the existing schemas import to include `SyncResult`:

```python
from app.models.schemas import (
    Transaction, TransactionSummary, CategorySummary,
    EmailMessage, DateRange, CreateTransactionRequest, SyncResult
)
```

and add this method directly below `_process_emails`:

```python
    async def force_sync(self, date_range: DateRange) -> SyncResult:
        """Re-fetch a date range from Gmail regardless of sync_info coverage.

        Message-id dedup makes a forced re-fetch safe and cheap; the range is
        marked synced only when every email parsed (same contract as the
        lazy path).
        """
        query = self._build_gmail_query(date_range)
        emails = self.gmail_service.get_messages(query)

        stored, skipped, failed_dates = await self._process_emails(emails)

        if failed_dates:
            logger.error(
                f"{len(failed_dates)} email(s) failed to parse in forced sync "
                f"{date_range.start_date}..{date_range.end_date} "
                f"(email dates: {failed_dates}); range not marked synced"
            )
        else:
            SyncInfoCrud.update_last_sync(self.db, date_range.start_date, date_range.end_date)

        sync_info = SyncInfoCrud.get_last_sync(self.db)
        return SyncResult(
            fetched=len(emails),
            stored=stored,
            skipped=skipped,
            failed=len(failed_dates),
            last_sync_date=sync_info.last_sync_date if sync_info else None,
        )
```

- [ ] **Step 4: Run the full suite**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 30 passed (27 + 3 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/schemas.py backend/app/services/transaction_service.py backend/tests/test_force_sync.py
git commit -m "feat: force_sync re-fetches a range from Gmail, dedup-safe

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Sync router (`GET /sync/status`, `POST /sync`) + wiring + docs

**Files:**
- Create: `backend/app/api/api_v1/routers/sync_router.py`
- Modify: `backend/app/main.py` (import + include_router)
- Modify: `CLAUDE.md` (routers list line)
- Test: `backend/tests/test_sync_endpoints.py` (create)

**Interfaces:**
- Consumes: `force_sync`, `SyncStatus`/`SyncRequest`/`SyncResult` (Task 2), `sync_fakes.FakeClassifier`/`make_email` (Task 1), `GmailAPIError` (`app/core/exceptions.py`), `verify_api_key` (existing).
- Produces: routes `GET /api/v1/sync/status` and `POST /api/v1/sync` — Task 5's frontend calls them.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_sync_endpoints.py`:

```python
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.api_v1.dependencies import get_transaction_service
from app.core.exceptions import GmailAPIError
from app.db.base_class import Base
from app.db.crud import SyncInfoCrud
from app.main import app
from app.services.transaction_service import TransactionService
from sync_fakes import FakeClassifier, make_email

AUTH = {"X-API-Key": "test-api-key"}

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


class OneBatchGmail:
    def __init__(self, emails):
        self.emails = emails

    def get_messages(self, query):
        return self.emails


class FailingGmail:
    def get_messages(self, query):
        raise GmailAPIError("Gmail unavailable")


@pytest.fixture()
def make_client(db_session):
    """Factory: build a TestClient whose service uses the given Gmail fake.

    Teardown always removes the override (the deferred fixture-cleanup
    pattern from the security-lockdown review).
    """
    def _make(gmail):
        service = TransactionService(
            gmail_service=gmail, classifier=FakeClassifier(), db=db_session
        )
        app.dependency_overrides[get_transaction_service] = lambda: service
        return TestClient(app)

    yield _make
    app.dependency_overrides.pop(get_transaction_service, None)


def test_sync_status_empty(make_client):
    response = make_client(OneBatchGmail([])).get("/api/v1/sync/status", headers=AUTH)
    assert response.status_code == 200
    assert response.json() == {
        "last_sync_date": None,
        "synced_start_date": None,
        "synced_end_date": None,
    }


def test_sync_status_reports_range(make_client, db_session):
    SyncInfoCrud.update_last_sync(db_session, datetime(2026, 6, 1), datetime(2026, 6, 30))
    body = make_client(OneBatchGmail([])).get("/api/v1/sync/status", headers=AUTH).json()
    assert body["synced_start_date"] == "2026-06-01T00:00:00"
    assert body["synced_end_date"] == "2026-06-30T00:00:00"
    assert body["last_sync_date"] is not None


def test_post_sync_returns_counts(make_client):
    client = make_client(OneBatchGmail([make_email("m1")]))
    response = client.post(
        "/api/v1/sync",
        json={"start_date": "2026-06-14T00:00:00", "end_date": "2026-06-16T23:59:59"},
        headers=AUTH,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["fetched"] == 1
    assert body["stored"] == 1
    assert body["failed"] == 0
    assert body["last_sync_date"] is not None


def test_post_sync_rejects_inverted_range(make_client):
    response = make_client(OneBatchGmail([])).post(
        "/api/v1/sync",
        json={"start_date": "2026-06-16T00:00:00", "end_date": "2026-06-14T00:00:00"},
        headers=AUTH,
    )
    assert response.status_code == 400


def test_post_sync_requires_body(make_client):
    response = make_client(OneBatchGmail([])).post("/api/v1/sync", json={}, headers=AUTH)
    assert response.status_code == 422


def test_post_sync_gmail_failure_returns_502(make_client):
    response = make_client(FailingGmail()).post(
        "/api/v1/sync",
        json={"start_date": "2026-06-14T00:00:00", "end_date": "2026-06-16T23:59:59"},
        headers=AUTH,
    )
    assert response.status_code == 502
    assert "Gmail" in response.json()["detail"]


def test_sync_requires_api_key(make_client):
    response = make_client(OneBatchGmail([])).get("/api/v1/sync/status")
    assert response.status_code == 401
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_sync_endpoints.py -v`
Expected: FAIL — the status/sync routes return 404 (router doesn't exist yet). The 401 test may already pass (auth wraps everything); that's fine.

- [ ] **Step 3: Implement the router and wire it**

Create `backend/app/api/api_v1/routers/sync_router.py`:

```python
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
```

In `backend/app/main.py`, add the import next to the other routers:

```python
from app.api.api_v1.routers.sync_router import router as sync_router
```

and after the existing two `include_router` calls:

```python
app.include_router(
    sync_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)
```

In `CLAUDE.md`, replace:

> - `api/api_v1/routers/` — `transactions_router.py` (list/count/create/delete/toggle-exclude) and `category_rules_router.py` (CRUD for classification rules). Wired in `main.py` under `/api/v1`.

with:

> - `api/api_v1/routers/` — `transactions_router.py` (list/count/create/delete/toggle-exclude), `category_rules_router.py` (CRUD for classification rules), and `sync_router.py` (sync status + manual force-sync). Wired in `main.py` under `/api/v1`.

- [ ] **Step 4: Run the full backend suite**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 38 passed (30 + 8 new).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/api_v1/routers/sync_router.py backend/app/main.py backend/tests/test_sync_endpoints.py CLAUDE.md
git commit -m "feat: sync status endpoint and manual force-sync endpoint

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Top spending category — backend fields + App wiring

**Files:**
- Modify: `backend/app/models/schemas.py` (`TransactionSummary`)
- Modify: `backend/app/services/transaction_service.py` (`get_summary` return)
- Modify: `frontend/src/App.jsx` (import + render `TopSpendingCategory`)
- Test: `backend/tests/test_summary.py` (create)

**Interfaces:**
- Consumes: existing `get_summary` / `TransactionSummary`; the committed `frontend/src/components/TopSpendingCategory.jsx` (reads `summary.top_spending_category` and `summary.top_spending_category_amount`; needs NO changes).
- Produces: `TransactionSummary.top_spending_category: Optional[str]`, `TransactionSummary.top_spending_category_amount: Optional[Decimal]`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_summary.py`:

```python
import asyncio
import uuid
from datetime import datetime
from decimal import Decimal

from app.models.schemas import Transaction
from app.services.transaction_service import TransactionService


def make_transaction(merchant, amount, category, excluded=False):
    return Transaction(
        id=uuid.uuid4(),
        date=datetime(2026, 6, 15, 12, 30),
        amount=Decimal(amount),
        merchant=merchant,
        primary_category=category,
        subcategory="General",
        confidence=0.9,
        description="test",
        excluded=excluded,
    )


# get_summary touches neither Gmail, the classifier, nor the DB.
SERVICE = TransactionService(gmail_service=None, classifier=None, db=None)


def test_top_spending_category_is_largest_total():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries"),
        make_transaction("PRICESMART", "2000.00", "Groceries"),
        make_transaction("COFFEE SPOT", "500.00", "Dining"),
    ]))
    assert summary.top_spending_category == "Groceries"
    assert summary.top_spending_category_amount == Decimal("3000.00")


def test_top_spending_category_ignores_excluded():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries"),
        make_transaction("CASINO", "9000.00", "Entertainment", excluded=True),
    ]))
    assert summary.top_spending_category == "Groceries"
    assert summary.top_spending_category_amount == Decimal("1000.00")


def test_top_spending_category_none_when_empty():
    summary = asyncio.run(SERVICE.get_summary([]))
    assert summary.top_spending_category is None
    assert summary.top_spending_category_amount is None


def test_top_spending_category_none_when_all_excluded():
    summary = asyncio.run(SERVICE.get_summary([
        make_transaction("HI-LO", "1000.00", "Groceries", excluded=True),
    ]))
    assert summary.top_spending_category is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_summary.py -v`
Expected: the first two FAIL with `AttributeError: 'TransactionSummary' object has no attribute 'top_spending_category'`; the empty/all-excluded ones also fail the same way.

- [ ] **Step 3: Add the fields and computation**

In `backend/app/models/schemas.py`, inside `TransactionSummary`, after `merchants: List[str]` add:

```python
    top_spending_category: Optional[str] = None
    top_spending_category_amount: Optional[Decimal] = None
```

In `backend/app/services/transaction_service.py`, in `get_summary`, replace the final `return TransactionSummary(...)` block with:

```python
        top_spending_category = None
        top_spending_category_amount = None
        if primary_categories:
            top_spending_category, top_summary = max(
                primary_categories.items(), key=lambda item: item[1].total
            )
            top_spending_category_amount = top_summary.total

        return TransactionSummary(
            total_spending=sum(t.amount for t in included_transactions),
            transaction_count=len(included_transactions),
            average_transaction=sum(t.amount for t in included_transactions) / len(transactions),
            by_primary_category=dict(primary_categories),
            by_subcategory=dict(subcategories),
            by_card_type=dict(card_types),
            merchants=list(set(t.merchant for t in included_transactions)),
            top_spending_category=top_spending_category,
            top_spending_category_amount=top_spending_category_amount,
        )
```

(Leave the `average_transaction` line exactly as-is — its denominator bug is roadmap item 4. `_empty_summary` needs no change: the new fields default to `None`.)

In `frontend/src/App.jsx`, add the import with the other component imports:

```javascript
import TopSpendingCategory from "./components/TopSpendingCategory";
```

and render it above `TransactionSummary` inside the existing `space-y-6` container:

```jsx
        <div className="space-y-6">
          <ErrorBoundary>
            <TopSpendingCategory />
          </ErrorBoundary>
          <ErrorBoundary>
            <TransactionSummary />
          </ErrorBoundary>
          <ErrorBoundary>
            <TransactionList />
          </ErrorBoundary>
        </div>
```

- [ ] **Step 4: Run both suites**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: 42 passed.
Run: `cd frontend && CI=true npm test -- --watchAll=false`
Expected: same as baseline — 3 suites pass, `App.test.js` fails on the pre-existing axios-ESM issue.

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/schemas.py backend/app/services/transaction_service.py backend/tests/test_summary.py frontend/src/App.jsx
git commit -m "feat: compute and display top spending category

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 5: Frontend sync control

**Files:**
- Modify: `frontend/src/services/api.js` (two functions)
- Create: `frontend/src/components/SyncControl.jsx`
- Modify: `frontend/src/App.jsx` (toolbar wiring)
- Test: `frontend/src/components/SyncControl.test.jsx` (create)

**Interfaces:**
- Consumes: `GET /sync/status` and `POST /sync` (Task 3, snake_case body keys), `useDateRange().appliedDateRange` (`{startDate: Date, endDate: Date}`), `useTransactionContext().refetch`.
- Produces: `getSyncStatus()` and `triggerSync({startDate, endDate})` in `services/api.js`; `<SyncControl />` component.

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/SyncControl.test.jsx`:

```jsx
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "../context/DateRangeContext";
import { TransactionProvider } from "../context/TransactionContext";
import SyncControl from "./SyncControl";
import * as apiModule from "../services/api";

jest.mock("../services/api");

const renderControl = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DateRangeProvider>
        <TransactionProvider>
          <SyncControl />
        </TransactionProvider>
      </DateRangeProvider>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.resetAllMocks();
  apiModule.fetchTransactions.mockResolvedValue({
    transactions: [],
    transaction_summary: null,
    categories: {},
  });
  apiModule.getTransactionCount.mockResolvedValue(0);
  apiModule.getSyncStatus.mockResolvedValue({
    last_sync_date: new Date().toISOString(),
    synced_start_date: "2026-06-01T00:00:00",
    synced_end_date: "2026-06-30T23:59:59",
  });
});

test("shows last-synced time and a Sync now button", async () => {
  renderControl();
  expect(await screen.findByText(/Last synced:/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sync now/i })).toBeInTheDocument();
});

test("triggers a sync for the applied date range on click", async () => {
  apiModule.triggerSync.mockResolvedValue({
    fetched: 2, stored: 1, skipped: 1, failed: 0,
    last_sync_date: new Date().toISOString(),
  });
  renderControl();
  await userEvent.click(screen.getByRole("button", { name: /sync now/i }));
  await waitFor(() => expect(apiModule.triggerSync).toHaveBeenCalledTimes(1));
  const arg = apiModule.triggerSync.mock.calls[0][0];
  expect(arg.startDate).toBeInstanceOf(Date);
  expect(arg.endDate).toBeInstanceOf(Date);
});

test("shows a warning when some emails failed to parse", async () => {
  apiModule.triggerSync.mockResolvedValue({
    fetched: 3, stored: 1, skipped: 0, failed: 2,
    last_sync_date: new Date().toISOString(),
  });
  renderControl();
  await userEvent.click(screen.getByRole("button", { name: /sync now/i }));
  expect(
    await screen.findByText(/2 email\(s\) couldn't be parsed/)
  ).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd frontend && CI=true npm test -- --watchAll=false -t "Sync now"`
Expected: FAIL — `Cannot find module './SyncControl'` (suite error counts as failure).

- [ ] **Step 3: Implement api functions and the component**

Append to `frontend/src/services/api.js`:

```javascript
export const getSyncStatus = async () => {
  try {
    const { data } = await api.get("/sync/status");
    return data;
  } catch (error) {
    throw new Error(`Failed to fetch sync status: ${error.message}`);
  }
};

export const triggerSync = async ({ startDate, endDate }) => {
  try {
    const { data } = await api.post("/sync", {
      start_date: startDate instanceof Date ? startDate.toISOString() : startDate,
      end_date: endDate instanceof Date ? endDate.toISOString() : endDate,
    });
    return data;
  } catch (error) {
    throw new Error(`Failed to sync: ${error.message}`);
  }
};
```

Create `frontend/src/components/SyncControl.jsx`:

```jsx
import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getSyncStatus, triggerSync } from "../services/api";
import { useDateRange } from "../context/DateRangeContext";
import { useTransactionContext } from "../context/TransactionContext";

const formatRelative = (isoDate) => {
  if (!isoDate) return null;
  const then = new Date(isoDate);
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return then.toLocaleDateString();
};

const SyncControl = () => {
  const [syncing, setSyncing] = useState(false);
  const [warning, setWarning] = useState(null);
  const queryClient = useQueryClient();
  const { appliedDateRange } = useDateRange();
  const { refetch } = useTransactionContext();

  const { data: status } = useQuery({
    queryKey: ["syncStatus"],
    queryFn: getSyncStatus,
  });

  const handleSync = async () => {
    setSyncing(true);
    setWarning(null);
    try {
      const result = await triggerSync({
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
      });
      if (result.failed > 0) {
        setWarning(
          `${result.failed} email(s) couldn't be parsed — they'll be retried automatically`
        );
      }
      queryClient.invalidateQueries({ queryKey: ["syncStatus"] });
      queryClient.invalidateQueries({ queryKey: ["transactionCount"] });
      await refetch();
    } catch (error) {
      setWarning(error.message);
    } finally {
      setSyncing(false);
    }
  };

  const lastSynced = formatRelative(status?.last_sync_date);

  return (
    <div className="flex items-center gap-3">
      {warning && <span className="text-sm text-amber-600">{warning}</span>}
      <span className="text-sm text-gray-500 whitespace-nowrap">
        {lastSynced ? `Last synced: ${lastSynced}` : "Never synced"}
      </span>
      <button
        onClick={handleSync}
        disabled={syncing}
        className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 whitespace-nowrap"
      >
        {syncing ? "Syncing…" : "Sync now"}
      </button>
    </div>
  );
};

export default SyncControl;
```

In `frontend/src/App.jsx`, add the import:

```javascript
import SyncControl from "./components/SyncControl";
```

and change the toolbar group from:

```jsx
          <div className="flex gap-2">
            <CategoryFilter />
```

to:

```jsx
          <div className="flex gap-2 items-center">
            <SyncControl />
            <CategoryFilter />
```

- [ ] **Step 4: Run the frontend suite**

Run: `cd frontend && CI=true npm test -- --watchAll=false`
Expected: SyncControl suite passes (3 tests); baseline otherwise (pre-existing `App.test.js` failure only).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/api.js frontend/src/components/SyncControl.jsx frontend/src/components/SyncControl.test.jsx frontend/src/App.jsx
git commit -m "feat: sync status display and manual Sync now control

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 6: CSV export

**Files:**
- Create: `frontend/src/utils/csv.js`
- Create: `frontend/src/utils/csv.test.js`
- Modify: `frontend/src/components/TransactionList.jsx` (imports, state, handler, header button)

**Interfaces:**
- Consumes: existing `fetchTransactions` (`services/api.js`), `useDateRange().appliedDateRange`, `useTransactionContext().filters`.
- Produces: `buildTransactionsCsv(transactions) -> string` (RFC-4180, `\r\n` line endings, fixed column order below).

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/utils/csv.test.js`:

```javascript
import { buildTransactionsCsv } from "./csv";

const HEADER =
  "date,merchant,amount,original_currency,original_amount,exchange_rate,primary_category,subcategory,confidence,card_type,source,excluded,description";

const tx = {
  date: "2026-06-15T12:30:00",
  merchant: "COFFEE SPOT",
  amount: 1500,
  original_currency: "JMD",
  original_amount: 1500,
  exchange_rate: null,
  primary_category: "Food & Dining",
  subcategory: "Coffee Shops",
  confidence: 0.9,
  card_type: "NCB VISA PLATINUM",
  source: "email",
  excluded: false,
  description: "test",
};

test("builds a header row plus one line per transaction", () => {
  const csv = buildTransactionsCsv([tx]);
  const lines = csv.split("\r\n");
  expect(lines).toHaveLength(2);
  expect(lines[0]).toBe(HEADER);
  expect(lines[1]).toContain("COFFEE SPOT");
  expect(lines[1]).toContain("1500");
});

test("escapes fields containing commas, quotes, and newlines", () => {
  const csv = buildTransactionsCsv([
    { ...tx, merchant: 'BURGER, THE "KING"', description: "line1\nline2" },
  ]);
  expect(csv).toContain('"BURGER, THE ""KING"""');
  expect(csv).toContain('"line1\nline2"');
});

test("renders null/undefined as empty; empty list is just the header", () => {
  expect(buildTransactionsCsv([])).toBe(HEADER);
  const csv = buildTransactionsCsv([
    { ...tx, exchange_rate: null, card_type: undefined },
  ]);
  const fields = csv.split("\r\n")[1].split(",");
  expect(fields[5]).toBe(""); // exchange_rate
  expect(fields[9]).toBe(""); // card_type
});
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd frontend && CI=true npm test -- --watchAll=false -t "header row"`
Expected: FAIL — `Cannot find module './csv'`.

- [ ] **Step 3: Implement the helper and the button**

Create `frontend/src/utils/csv.js`:

```javascript
const HEADERS = [
  "date",
  "merchant",
  "amount",
  "original_currency",
  "original_amount",
  "exchange_rate",
  "primary_category",
  "subcategory",
  "confidence",
  "card_type",
  "source",
  "excluded",
  "description",
];

const escapeField = (value) => {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

export const buildTransactionsCsv = (transactions) => {
  const rows = transactions.map((tx) =>
    HEADERS.map((header) => escapeField(tx[header])).join(",")
  );
  return [HEADERS.join(","), ...rows].join("\r\n");
};
```

In `frontend/src/components/TransactionList.jsx`:

1. Extend the api import and add the new imports:

```javascript
import {
  toggleTransactionExclusion as apiToggleExclusion,
  fetchTransactions,
} from "../services/api";
import { buildTransactionsCsv } from "../utils/csv";
import { useDateRange } from "../context/DateRangeContext";
```

2. Inside the component, next to the other `useState` calls:

```javascript
  const { appliedDateRange } = useDateRange();
  const [exporting, setExporting] = useState(false);
```

3. Add the handler next to the other handlers:

```javascript
  const handleExport = async () => {
    setExporting(true);
    try {
      const data = await fetchTransactions({
        ...filters,
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
        limit: 1000,
        offset: 0,
      });
      const csv = buildTransactionsCsv(data.transactions || []);
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      const day = (d) => d.toISOString().slice(0, 10);
      link.href = url;
      link.download = `fi-mi-cash-${day(appliedDateRange.startDate)}-${day(appliedDateRange.endDate)}.csv`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to export CSV:", error.message);
    } finally {
      setExporting(false);
    }
  };
```

4. In the Table Header block, after the `<div className="sm:flex-auto">…</div>` closes (still inside `<div className="sm:flex sm:items-center mb-4">`), add:

```jsx
          <div className="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
            <button
              onClick={handleExport}
              disabled={exporting}
              className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            >
              {exporting ? "Exporting…" : "Export CSV"}
            </button>
          </div>
```

- [ ] **Step 4: Run the frontend suite**

Run: `cd frontend && CI=true npm test -- --watchAll=false`
Expected: csv suite passes (3 tests); baseline otherwise.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/csv.js frontend/src/utils/csv.test.js frontend/src/components/TransactionList.jsx
git commit -m "feat: export current filtered view as CSV

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 7: End-to-end smoke of the sync endpoints

**Files:**
- No source changes expected; scratch files only (use the session scratchpad, never the repo or `backend/app/`).

**Interfaces:**
- Consumes: everything above.

- [ ] **Step 1: Smoke the endpoints against a real server**

From a scratch directory (same recipe as item 3's Task 6 — never the real `backend/app/` CWD):

1. Scratch CWD with `.env`: `API_KEY=e2e-test-key`, `OPENAI_API_KEY=dummy`, `GMAIL_CREDENTIALS_PATH=credentials.json` (file need not exist; Gmail is lazily initialized).
2. Start: `cd <scratch> && <repo>/backend/.venv/bin/python -m uvicorn app.main:app --port 8099 --app-dir <repo>/backend`, output captured to a log file.
3. `curl -s -H "X-API-Key: e2e-test-key" http://127.0.0.1:8099/api/v1/sync/status` → 200 with all-null fields (fresh DB).
4. `curl -s http://127.0.0.1:8099/api/v1/sync/status` (no key) → 401.
5. `curl -s -X POST -H "X-API-Key: e2e-test-key" -H "Content-Type: application/json" -d '{"start_date":"2026-07-01T00:00:00","end_date":"2026-07-04T23:59:59"}' http://127.0.0.1:8099/api/v1/sync` → expected **502** with a Gmail-initialization detail (no credentials in scratch) — this proves the route, validation, and error path work end-to-end without real credentials.
6. `curl -s -X POST -H "X-API-Key: e2e-test-key" -H "Content-Type: application/json" -d '{"start_date":"2026-07-04T00:00:00","end_date":"2026-07-01T00:00:00"}' http://127.0.0.1:8099/api/v1/sync` → 400 (inverted range).
7. Kill the server (verify the port is free afterward) and delete the scratch dir.

- [ ] **Step 2: Full suites one final time**

Run: `cd backend && .venv/bin/python -m pytest tests -v` — expected 42 passed.
Run: `cd frontend && CI=true npm test -- --watchAll=false` — expected: all suites pass except the pre-existing `App.test.js` axios-ESM failure.

Write the evidence (commands + trimmed output) to the SDD report file for this task.

---

## Self-review notes

- Spec coverage: §1 endpoints → Tasks 2–3 (pipeline refactor Task 1); §2 sync UI → Task 5; §3 top category → Task 4; §4 CSV → Task 6; testing section → per-task tests + Task 7 smoke.
- Type consistency: `_process_emails(emails) -> (stored, skipped, failed_dates)` (Tasks 1, 2); `force_sync(date_range) -> SyncResult` (Tasks 2, 3); `SyncStatus`/`SyncRequest`/`SyncResult` field names identical in schemas, router, endpoint tests, and frontend (`last_sync_date`, `failed`); `sync_fakes` exports used by Tasks 2–3 match Task 1's file; `buildTransactionsCsv` name identical in Task 6's helper/tests/component.
- The router 502 test relies on `GmailAPIError` bubbling from `get_messages`; `FailingGmail` raises it directly — no real Gmail touched anywhere.
