# Sync Visibility + Extras — Design

**Date:** 2026-07-04
**Source:** docs/ROADMAP.md §5 item 7 ("Add sync visibility, then finish the
extras") — sync status + manual "Sync now", complete top-spending-category,
CSV export (Section 4 features 4–6).
**Scope:** New sync endpoints + toolbar control, `TransactionSummary` top-category
fields + wiring the committed `TopSpendingCategory.jsx`, client-side CSV export.
Out of scope: background/queued sync, a server-side "sync in progress" flag,
merchant search and original-currency display (item 6), month-over-month trends,
items 4–5 (stat bugs, classifier split-brain — still open).

## Goal

Close the "sync happens invisibly" gap: show when data was last synced, let the
user force a re-fetch (new emails arriving inside an already-marked-synced range
are otherwise never fetched — the stale-today hole), and ship two small extras:
the top-spending-category card whose frontend half is already committed, and CSV
export of the current filtered view.

Decisions taken with the user:

- **"Sync now" is a force sync** of the currently applied date range: it
  re-fetches from Gmail regardless of `sync_info` coverage. Item 3's message-ID
  dedup makes this safe (no duplicates) and cheap (already-stored emails skip
  parse/classification).
- **CSV export is client-side**: reuse `GET /transactions` with the current
  filters and the backend's 1000-row cap; build and download the blob in the
  browser. No new backend export surface.

## Design

### 1. Backend sync endpoints — new `api/api_v1/routers/sync_router.py`

- **`GET /sync/status`** → `SyncStatus` schema:
  `{last_sync_date: Optional[datetime], synced_start_date: Optional[datetime],
  synced_end_date: Optional[datetime]}` — all `None` when no `sync_info` row
  exists. Reads `SyncInfoCrud.get_last_sync`.
- **`POST /sync`** with JSON body `{start_date: datetime, end_date: datetime}`
  (Pydantic `SyncRequest`; 422 on missing/invalid, 400 if `start_date >
  end_date`) → runs `TransactionService.force_sync(date_range)` and returns
  `SyncResult {fetched: int, stored: int, skipped: int, failed: int,
  last_sync_date: Optional[datetime]}`.
- `force_sync` builds the same Gmail query as lazy sync for the full requested
  range (no gap detection), processes every email through the shared pipeline
  (below), then marks the range synced via `SyncInfoCrud.update_last_sync`
  **only when `failed == 0`** — the same integrity contract as item 3's lazy
  path. `last_sync_date` in the response reflects the post-sync row (or `None`
  if never synced and this run failed to mark).
- A `GmailAPIError` from the fetch surfaces as HTTP 502 with the error detail
  (not a silent no-op).
- **Shared pipeline refactor:** the per-email loop inside `_sync_transactions`
  (message-ID skip → parse with belt-and-braces except → legacy NULL-id check →
  insert with `IntegrityError` swallow+rollback) is extracted into
  `TransactionService._process_emails(emails) -> (stored: int, skipped: int,
  failed_dates: list[datetime])`, used by both the lazy path and `force_sync`.
  Lazy-path behavior is unchanged (per-gap marking only when its
  `failed_dates` is empty; same per-gap error log).
- Router wired in `main.py` under the existing `verify_api_key` dependency,
  same as the other routers.

### 2. Frontend sync control

- `services/api.js`: `getSyncStatus()` (GET `/sync/status`) and
  `triggerSync({startDate, endDate})` (POST `/sync`, ISO strings in
  snake_case body keys) on the shared axios instance.
- New `components/SyncControl.jsx`, rendered in the `App.jsx` toolbar row next
  to `DateRangePicker`:
  - "Last synced: <relative time>" from a React Query
    (`queryKey: ["syncStatus"]`) on `getSyncStatus`; renders "Never synced"
    when null.
  - **Sync now** button: POSTs the applied range from `useDateRange()`
    (`appliedDateRange`), disabled with a spinner while in flight; on success
    invalidates/refetches the transaction list, count, and sync-status
    queries.
  - When the result has `failed > 0`, show an inline warning
    ("N emails couldn't be parsed — they'll be retried automatically") rather
    than a success state.
- Limitation (accepted): the "syncing" signal is the button's request-scoped
  state; syncs triggered inline by `GET /transactions` show no indicator.

### 3. Top spending category

- `TransactionSummary` schema (`models/schemas.py`) gains
  `top_spending_category: Optional[str] = None` and
  `top_spending_category_amount: Optional[Decimal] = None`.
- `TransactionService.get_summary` sets them from the max of
  `by_primary_category` by `total` (ties: max() picks one — acceptable);
  `_empty_summary` leaves them `None`. The committed `TopSpendingCategory.jsx`
  already guards null/zero and needs no changes.
- `App.jsx` imports and renders `TopSpendingCategory` in the summary section
  (inside the existing `space-y-6` container, above `TransactionSummary`,
  wrapped in `ErrorBoundary` like its siblings).

### 4. CSV export

- New pure helper `src/utils/csv.js`: `buildTransactionsCsv(transactions) ->
  string` with RFC-4180 quoting (fields containing `"`, `,`, or newlines are
  double-quoted with `""` escapes). Columns: date, merchant, amount,
  original_currency, original_amount, exchange_rate, primary_category,
  subcategory, confidence, card_type, source, excluded, description.
- **Export CSV** button in `TransactionList`'s header: calls
  `fetchTransactions` with the current filters/date range and
  `limit: 1000, offset: 0` (backend cap), builds the CSV, downloads via
  Blob + object URL as `fi-mi-cash-<startDate>-<endDate>.csv`. Disabled while
  exporting; surfaces fetch errors via the existing error style.

## Testing

- **Backend (TDD):** `force_sync` unit tests reusing the fakes pattern from
  `tests/test_sync_integrity.py` (counts fetched/stored/skipped/failed;
  marks range only when clean; dedup-skip on re-sync; GmailAPIError → raises).
  Endpoint tests for `GET /sync/status` (empty + populated) and `POST /sync`
  (result counts, 400 on inverted range, 422 on bad body) via `TestClient`
  with a `dependency_overrides` **fixture with teardown** (pays down the
  deferred minor from item 1 now that several modules override dependencies).
  `get_summary` tests for top-category fields (normal, tie-free max, empty,
  all-excluded → `None`).
- **Frontend (Jest):** `buildTransactionsCsv` unit tests (quoting/escaping,
  header row, empty list); `SyncControl` render + click test with mocked api
  (same style as `CategoryEditModal.test.jsx`).
- Existing suites keep passing: backend
  `.venv/bin/python -m pytest tests -v`; frontend
  `CI=true npm test -- --watchAll=false` (pre-existing `App.test.js`
  axios-ESM failure excepted).
