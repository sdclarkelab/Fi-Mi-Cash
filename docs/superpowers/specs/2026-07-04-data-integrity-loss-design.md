# Data-Integrity Loss — Design

**Date:** 2026-07-04
**Source:** docs/ROADMAP.md §5 item 3 ("Fix data-integrity loss")
**Scope:** `transaction_exists` dedup keyed on Gmail message ID; parse
failures surface and keep their sync gap un-marked so it is retried.
Out of scope: sync-status endpoint/UI (item 7), backfilling message IDs for
legacy rows, the classifier split-brain (item 5), OpenAI JSON response mode.

## Goal

Close the Critical audit finding (dedup on exact `(date, amount, merchant)`
silently drops a legitimate second same-day purchase — permanent, unrecoverable
under-reporting) and the High finding (an email that fails to parse is dropped
with only a log line while the whole range is marked synced, so gap detection
never re-fetches it — the transaction is permanently missing).

Decisions taken with the user:

- Failure handling: a gap with any parse/classification failure is **not
  marked synced** — every later view retries it until it succeeds (roadmap's
  suggestion). No failure table, no count-and-log-only.
- Keep the DB-level unique index on the new message-ID column.

## Design

### 1. Dedup on Gmail message ID

The Gmail message ID is already fetched (`msg['id']`,
`gmail_service.py:75`) but discarded. Carry it end-to-end:

- **`EmailMessage`** (`models/schemas.py`) gains `message_id: str`;
  `GmailService._fetch_email_message` populates it from `msg['id']`.
- **`TransactionModel`** (`models/transaction_model.py`) gains
  `email_message_id = Column(String, nullable=True, index=True)` — NULL for
  manual transactions and legacy (pre-migration) rows. The Pydantic
  `Transaction` schema gains the same optional field;
  `TransactionCrud.create_transaction`, `TransactionService._to_transaction`,
  and `_parse_transaction` carry it through.
- **Unique partial index** on the model:
  `Index(..., unique=True, sqlite_where=email_message_id.isnot(None))` —
  DB-level enforcement that also closes most of the concurrent-sync
  duplicate-insert race (audit Medium).
- **Dedup logic** in `_sync_transactions`, per email, in order:
  1. `TransactionCrud.transaction_exists_by_message_id(db, email.message_id)`
     — checked **before** parsing, so an already-stored email skips both the
     regex parse and the OpenAI classification call (today classification runs
     before the dedup check and is re-paid on every re-fetch).
  2. Legacy fallback: after a successful parse, the old
     `(date, amount, merchant)` exact-match check, but **only against rows
     where `email_message_id IS NULL`** — pre-migration rows must not
     duplicate when the sliding sync window (`MAX_SYNC_DAYS` truncation)
     re-fetches an old range. Because every newly synced row has a message ID,
     this fallback can never match another new row, so two same-day
     identical-amount purchases (distinct emails → distinct message IDs) now
     both store.

### 2. Schema migration — startup ALTER

There is no alembic, and `Base.metadata.create_all()` never ALTERs an
existing table; the live `transactions.db` holds real data.

- A small idempotent migration step runs at startup next to `create_all()`
  (in `main.py`'s startup path or `db/database.py`): if
  `PRAGMA table_info(transactions)` lacks `email_message_id`, run
  `ALTER TABLE transactions ADD COLUMN email_message_id VARCHAR`, then
  `CREATE UNIQUE INDEX IF NOT EXISTS ix_transactions_email_message_id ON
  transactions(email_message_id) WHERE email_message_id IS NOT NULL`.
- Idempotent by construction (column check + `IF NOT EXISTS`); a fresh DB gets
  the column and index from `create_all()` and the migration no-ops.
- No backfill: legacy rows keep NULL and rely on the fallback dedup check.

### 3. Parse failures keep their gap unsynced

Rework `_sync_transactions` (`services/transaction_service.py:59-79`) to
per-gap accounting:

- For each gap from `get_sync_gaps`: fetch emails; per email, skip if the
  message ID is already stored; otherwise parse and store. Count failures —
  `_parse_transaction` returning `None` (which includes classification
  errors swallowed by its blanket `except`) and any unexpected per-email
  exception.
- A gap that completes with **zero failures** is marked synced immediately via
  `update_last_sync(gap.start, gap.end)` — replacing today's single
  mark-everything call with the originally requested range. Per-gap marking is
  safe: `get_sync_gaps` only returns contiguous extensions of the tracked
  range (before its start / after its end), so marking one gap never falsely
  bridges an unsynced hole.
- A gap with ≥1 failure is **not** marked; the next request retries it. The
  pre-parse message-ID skip makes retries cheap — only the failing email is
  re-parsed/re-classified; siblings already stored are skipped.
- Failures raise a per-gap `logger.error` summarizing the failure count and
  the affected email dates; the existing per-email `logger.warning` inside
  `_parse_transaction` keeps the detail.
- Side benefit: a Gmail fetch failure in gap 2 no longer discards gap 1's
  successful sync (gap 1 was already marked when it completed).
- Known trade-off (accepted): a permanently unparseable email (e.g. a bank
  template change) keeps its gap re-fetching from Gmail on every request with
  an error logged each time — deliberate visible pressure that data is
  missing, until the parser is fixed. Observability beyond logs is roadmap
  item 7.

## Testing

TDD, extending `backend/tests` (mocked `GmailService`/classifier, in-memory
or tmp-file SQLite):

- **Dedup:** same message ID fetched twice → one row; two emails with
  identical `(date, amount, merchant)` but different message IDs → two rows;
  legacy NULL-ID row + re-fetched matching email → no duplicate; manual
  transactions (NULL message ID) unaffected by the unique index.
- **Sync marking:** gap containing one failing email → that gap's range not
  marked synced while successfully parsed siblings are stored; clean gap →
  marked; one clean + one failing gap → only the clean one marked.
- **Migration:** a legacy-schema SQLite file gains the column and index;
  running the migration twice is a no-op.
- Existing backend tests keep passing (`.venv/bin/python -m pytest tests -v`).
