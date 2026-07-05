# Fi-Mi-Cash — Current State & Roadmap

> Audited 2026-07-02 on branch `address-tech-debt` (full backend + frontend
> read; method and raw notes in docs/superpowers/plans/). For dev setup and
> architecture-for-coding, see CLAUDE.md. This doc: what the app does, what's
> wrong, what's missing, what to build next.

## 1. Current State

### What it does today

- **Gmail sync of NCB card alerts** — ingests transaction emails from
  `no-reply-ncbcardalerts@jncb.com`, parsing amount and merchant out of the alert HTML.
- **AI merchant categorization with editable rules** — new merchants are classified by
  OpenAI (`gpt-3.5-turbo`), guided by a user-editable rules file; results cached in a TTL cache.
- **Date-range and multi-select category filtering** of the transaction list.
- **Summaries** — totals and breakdowns by primary category, subcategory, and card type,
  plus transaction count and average.
- **Manual transactions** — add a transaction by hand via a modal.
- **Exclusion toggling** — mark a transaction excluded so it drops out of spending totals.
- **Deletion of manual transactions** (with source tracking).
- **Pagination** over the transaction list with a total-count query.
- **USD→JMD conversion** using historical exchange rates fetched from a public currency API,
  with a hardcoded fallback rate.

### How it works (behavior essentials)

- **Lazy sync-on-read with gap detection.** `GET /transactions` is backed by
  `TransactionService.get_transactions`, which first calls `_should_sync_transactions` and, if the
  requested date range has un-synced gaps, runs `_sync_transactions` inline before querying the DB.
  `SyncInfoCrud.get_sync_gaps()` diffs the requested range against a single `sync_info` row
  (`id="last_sync"`) to decide which sub-ranges to fetch from Gmail. A sliding window bounded by
  `MAX_SYNC_DAYS`/`SYNC_WINDOW_DAYS`/`MIN_SYNC_OVERLAP_HOURS` keeps the tracked range from growing
  unbounded. Ingest-time dedup is a separate, simpler `transaction_exists()` exact-match check.
- **Classification pipeline.** Per new merchant: check the file-based rules
  (`backend/app/data/classification_rules.json`, loaded once at construction) → if unmatched, call
  OpenAI (offloaded via `asyncio.to_thread`) → cache the result in an in-process `TTLCache`
  (`CACHE_TTL`/`CACHE_MAX_SIZE`).
- **A single `GET /transactions` response feeds the whole UI.** The React frontend uses React Query
  with two queries (list + total count) sharing the same filter/date state; there is no separate
  summary endpoint wired in (the dead `useSummary` hook aimed at one that was never built).
- **Data lives in SQLite** (`transactions.db`, CWD-relative). Two tables: `transactions` (one
  denormalized row per purchase, UUID string id) and `sync_info` (one row). Schema is created by
  `Base.metadata.create_all()` at startup — there is no migration tool (README's alembic is fictional).
- **No auth layer of any kind**; the API is composed per-request in
  `api/api_v1/dependencies.py` (the sole composition root).

### Work in progress on this branch

There is no active build-in-progress on `address-tech-debt` (the audit tasks made no
application-code commits). The one half-built artifact is **`TopSpendingCategory.jsx`**:

- It is **tracked, committed dead code** — committed in `c4d2569` ("feat: add top spending category")
  *before* this audit's work began, not untracked WIP on this branch.
- It is **unwired**: `grep -rn "TopSpendingCategory" frontend/src` matches only the component's own
  definition/export. Nothing in `frontend/src` imports or renders it, so the running app is unaffected.
- Its **backend contract was never implemented**: it reads `summary.top_spending_category` and
  `summary.top_spending_category_amount`, but `TransactionSummary` (`schemas.py:59-71`) has no such
  fields (`grep -rn "top_spending_category" backend/app` → zero matches). If wired in as-is it would
  permanently render its "No Data" placeholder (fails soft via an `&&` guard, does not crash).
- Net: dead code today, not a live bug. Finishing the feature requires the missing backend half
  (schema fields + computation in `get_summary`). See Section 4.

## 2. Issues (full audit, 2026-07-02)

39 verified findings. Each entry: **title** — `file:line` — impact. Ordered most-impactful-first
within each severity. Full reasoning and verification steps live in
`docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`.

### 🔴 Critical

- **No authentication on any endpoint** — `backend/app/api/api_v1/routers/transactions_router.py`,
  `.../category_rules_router.py`, `.../dependencies.py` — every endpoint (full history, create/delete,
  rule editing) is reachable by anyone who can reach the process, with zero identity or authz checks.
- **CORS allows any origin while allowing credentials** — `backend/app/main.py:38-44`
  (`allow_origins=["*"]` + `allow_credentials=True`, marked TODO) — combined with no-auth, any web page
  the user's browser visits while the backend runs can read or mutate/delete all transaction data.
- **`transaction_exists` dedup can silently drop a legitimate second same-day purchase** —
  `backend/app/db/crud.py:108-114` — dedup keys only on exact `(date, amount, merchant)`, so a genuine
  second identical-amount purchase from the same merchant on the same day is silently discarded (never
  stored, unrecoverable) with no error or log, under-reporting spend. *Upgraded from High: this is
  permanent data loss (Critical per the audit scale), and the trigger — two same-merchant same-amount
  purchases in a day — is common, not an edge case.*

### 🟠 High

- **Silent per-email parse failures never surface, and the sync range is still marked complete** —
  `backend/app/services/transaction_service.py:243-245,265-267,85-97` — an email that fails to parse
  (NCB template variation, truncated body) is dropped with only a log line, and because the whole range
  is marked synced afterward, gap detection never re-fetches it — the transaction is permanently missing.
- **Applying a date range truncates the end date to local midnight, dropping the entire end day** —
  `frontend/src/context/DateRangeContext.jsx:87-91`, `frontend/src/components/DateRangePicker.jsx:26-32,66-78`
  (vs `backend/app/db/crud.py:59-60`) — `startOfDay` floors `endDate` to `00:00:00`, so `date <= midnight`
  matches almost none of that day's transactions; list, count, and totals silently omit the end day on
  every Apply/Refresh.
- **Editing a transaction's category without checking "create rule" silently discards the edit** —
  `frontend/src/components/CategoryEditModal.jsx:39-57`, `frontend/src/components/TransactionList.jsx:82-98`
  — the only side-effecting path is gated behind the "create rule" checkbox; unchecked, the modal closes as
  if saved but nothing is persisted. There is no way to re-categorize a single transaction in isolation.
- **`average_transaction` divides by the wrong count when any transaction is excluded** —
  `backend/app/services/transaction_service.py:106,131-133` — numerator uses the included-only list but the
  denominator uses `len(transactions)` (unfiltered), so the headline average is understated the moment a
  user excludes even one transaction.
- **Two independent `MerchantClassifier` singletons — rule edits are invisible to Gmail-sync
  classification until process restart** — `backend/app/api/api_v1/dependencies.py:12-41`,
  `.../category_rules_router.py:14,21-22,43-44,67` — the rules router mutates one instance's in-memory
  rules; the sync path uses a different instance that loaded the rules file once at construction, so
  edited/deleted rules don't take effect for future classification until restart.
- **`get_categories` silently ignores the multi-select `categories` filter that
  `get_transactions`/`get_transaction_count` honor** — `backend/app/db/crud.py:143-185` — with an active
  multi-select category filter, the transaction list is scoped correctly but the filter dropdown reverts to
  categories from the entire unfiltered dataset — a user-visible query-result inconsistency.

### 🟡 Medium

- **Live secrets sit untracked in the working tree, one `git add -f` from exposure** —
  `backend/app/.env`, `credentials.json`, `token.json`, `transactions.db` — a real OpenAI key, Google OAuth
  secret, live Gmail token, and real financial DB are present but untracked; only gitignore protects them,
  and `.env.example` sits right beside `.env`. (Medium because untracked; would be Critical if committed.)
- **`classification_rules.json` is gitignored — category rules exist only on local disk** —
  `backend/.gitignore` (final line) — the rules asset is not version-controlled and has no backup; disk
  loss or a fresh clone loses/lacks all user-defined rules.
- **Database URL is hardcoded and CWD-relative; wrong working directory silently creates a fresh empty DB** —
  `backend/app/db/database.py:7-11` — launching from another directory silently creates a new empty
  `transactions.db`; the app looks healthy with zero data, and a later sync can fork the dataset.
- **Rules-persistence write failures are silent** — same swallowed-exception subsystem, two facets:
  - **`add_rule`/`edit_rule` report success even when the on-disk write fails** —
    `backend/app/services/classifier_service.py:42-50,72-98` — `_save_rules` logs-and-swallows disk errors;
    callers unconditionally `return True`, so a rule is usable in-memory but silently lost on restart.
  - **Non-atomic writes + silent fallback-to-defaults can permanently wipe user rules** —
    `backend/app/services/classifier_service.py:27-40,42-50` — a single non-atomic `open('w')` can leave
    truncated JSON on a crash; `_load_rules` then silently resets to the 9-entry defaults (live file has 19
    custom rules), and the next mutation overwrites the corrupted file with defaults — permanent, no backup.
- **`update_transactions_by_merchant` swallows every exception and returns 0, indistinguishable from
  "no rows matched"** — `backend/app/db/crud.py:126-140` — the retroactive-reclassify bulk update masks real
  DB failures (lock, constraint, connection) as a normal no-op, with no log; this class of bug is
  unobservable.
- **Hardcoded fallback USD→JMD rate silently used when the currency API is unavailable** —
  `backend/app/services/transaction_service.py:179-184` — any USD transaction parsed while the currency API
  is down is stored at a stale `Decimal('159')` rate, with no flag distinguishing it from a correct conversion.
- **Ingestion is hardwired to one sender and brittle HTML regexes; a bank template change silently ends
  ingestion** — `backend/app/services/transaction_service.py:187-195,209-210,231-232` — no config point for
  another sender/bank, and any NCB HTML change stops the regexes matching; combined with the silent-parse
  finding it fails soft (no alert), just an ever-growing set of unparsed, "synced" emails.
- **Classifier requests no JSON response mode from OpenAI, feeding the silent-transaction-drop path** —
  `backend/app/services/classifier_service.py:146-176` — no `response_format={"type":"json_object"}`, so a
  routine prose-prefixed or code-fenced reply fails `json.loads`, raises `ClassificationError`, and drops the
  entire transaction via `_parse_transaction`'s `except: return None`.
- **First request for an un-synced range performs Gmail fetch + per-merchant OpenAI classification
  synchronously inside the GET response** — `backend/app/services/transaction_service.py:33-54,77-97` — a
  normal read can take tens of seconds and fails wholesale if Gmail/OpenAI is slow or down, with no
  partial-result or sync-status signal — the user just sees a hung or failed page load.
- **Gmail API calls inside `_sync_transactions` are synchronous and unwrapped, blocking the asyncio event
  loop** — `backend/app/services/transaction_service.py:87`, `backend/app/services/gmail_service.py:67-105`
  — the blocking Gmail HTTP calls aren't wrapped in `asyncio.to_thread` (unlike the OpenAI call), so they
  stall the whole worker (all concurrent requests) for the sync duration. *Kept Medium, not High: the stall
  is transient, and the server-wide blast radius is largely theoretical in single-user personal use.*
- **Concurrent syncs of overlapping date ranges can race past the dedup check and insert duplicate rows** —
  `backend/app/services/transaction_service.py:77-97` — an `await` between parse and the check-then-create
  pair, with no lock or DB unique constraint, lets two overlapping first-time syncs (e.g. two tabs) both
  insert the same purchase, inflating totals. *Kept Medium, not High: it does produce wrong results, but only
  under a narrow concurrency race unlikely in single-user use (contrast the common trigger of the Critical
  dedup finding).*
- **Money columns are declared `Numeric`/`Decimal` end-to-end but SQLite physically stores them as
  floating-point `REAL`** — `backend/app/models/transaction_model.py:13,23,24`, `.../schemas.py:26,36,37` —
  ORM reads round-trip cleanly today, but any raw SQL aggregation (reporting script, DB browser) operates on
  IEEE-754 floats and is exposed to binary rounding error; the `Numeric(10,2)` precision isn't enforced by storage.
- **`TransactionSummary` schema lacks the `top_spending_category`/`top_spending_category_amount` fields the
  committed frontend component expects** — `backend/app/models/schemas.py:59-71`,
  `frontend/src/components/TopSpendingCategory.jsx:19-21,47-51` — a dead-code contract mismatch (component is
  unwired, so not a live bug); it blocks completing the top-spending-category feature until the backend half exists.
- **Mutations only `refetch()` the transaction-list query; the pagination total-count query is never
  refreshed** — `frontend/src/context/TransactionContext.jsx:26-38,41-58,90-102`,
  `frontend/src/App.jsx:60-62`, `frontend/src/components/TransactionList.jsx:69,94,105-107` — after add/delete
  the "Showing X of Z" text and page buttons stay stale (up to `staleTime: 30000` or until a filter change),
  and deleting the last item on the last page can strand the user on an empty page. *Downgraded from High to
  Medium: the stale count self-heals within 30s or on any filter change, so it's a transient UX defect rather
  than a persistent wrong-results bug like the High findings.*
- **`backend/requirements.txt` has only `>=` floors and no lockfile** — `backend/requirements.txt:1-12` —
  every fresh install resolves to newest (including future breaking majors); the environment is
  unreproducible and a reinstall can silently break the app.
- **Frontend is built on deprecated Create React App (`react-scripts 5.0.1`)** — `frontend/package.json:17`
  — the build toolchain is unmaintained (CRA deprecated Feb 2025); transitive vulns won't be patched and
  React/tooling upgrades are blocked until migration (e.g. to Vite). `package-lock.json` at least makes
  installs reproducible.

### ⚪ Low

- **Dead auth config: `SECRET_KEY`/`ACCESS_TOKEN_EXPIRE_MINUTES` defined but never consumed** —
  `backend/app/config.py:13-14` — dead code that makes auth look implemented; if wired up later without
  changing the default, the literal `"your-secret-key-here"` would ship as a real secret.
- **Gmail OAuth token persisted via `pickle`; refresh path assumes an interactive desktop session** —
  `backend/app/services/gmail_service.py:34-59` — `pickle.load` on `token.json` executes arbitrary bytecode
  if tampered, and `run_local_server` + browser launch hangs on a headless deployment when the token expires.
- **README describes a project that doesn't exist: alembic, lint tooling, env vars, file layout** —
  `README.md:98,106,132,150-158,181,201,241,243,277,282` — a new user following it hits a dead end at
  `alembic upgrade head` (not installed) and configures env vars the app never reads.
- **Currency display hardcodes JMD; original currency/amount and exchange rate are never shown** —
  `frontend/src/utils/formatters.js:1-6` (also `DeleteConfirmationModal.jsx:72` renders a raw unformatted
  amount) — `formatCurrency` always formats JMD and the UI reads none of the `original_*`/`exchange_rate`
  fields the backend returns (see Section 3 gap). Cosmetic here; the missing-capability half is a gap.
- **Mixed HTTP clients in `services/api.js`: axios (with a shared error interceptor) for transactions, raw
  `fetch` (no interceptor) for rules** — `frontend/src/services/api.js:6-22,82-138` — two inconsistent error
  paths; `getAllRules` is strictly worse, surfacing generic HTTP status text instead of the backend `detail`.
- **Two separate `declarative_base()` objects exist; one is dead and unused** —
  `backend/app/db/database.py:13` vs `backend/app/db/base_class.py:3` — no live bug (only `base_class.Base`
  is wired), but a future import of `database.Base` would silently skip that model's table in `create_all()`.
- **`get_gmail_service` is dead code — `get_transaction_service` builds a fresh, uncached `GmailService()`
  per request** — `backend/app/api/api_v1/dependencies.py:12-14,25` — the `@lru_cache` implies a caching
  design intent that never takes effect; misleading when reading the DI layer.
- **`delete_rule` doesn't retroactively update already-classified transactions, unlike `add_rule`/`update_rule`** —
  `backend/app/api/api_v1/routers/category_rules_router.py:64-81` — deleting a rule leaves old transactions
  in their rule-assigned category while new ones classify fresh, so a merchant can split across categories.
  (May be intentional — confirm intent before "fixing".)
- **`TopSpendingCategory.jsx` is unwired, committed dead code — half a feature with no route to the screen** —
  `frontend/src/components/TopSpendingCategory.jsx`, `frontend/src/App.jsx:1-11` — never imported/rendered;
  reads backend fields that don't exist. Tracked (committed `c4d2569`), not untracked WIP. See Section 1 and
  the Medium schema-mismatch finding.
- **Dead code: `useTransactions.js`, `useSummary.js` (also broken), empty `CategoryContext.jsx`;
  `useTransactionData.js` half-dead** — `frontend/src/hooks/useTransactions.js`, `.../useSummary.js`,
  `frontend/src/context/CategoryContext.jsx`, `.../hooks/useTransactionData.js` — none reachable from the app;
  `useSummary` imports a nonexistent `fetchSummary` and would throw if called. Only `transactionQueryKey` is live.
- **`Transaction`/`TransactionSummary` use Pydantic v1-style `class Config`, deprecated under installed
  Pydantic 2.9** — `backend/app/models/schemas.py:46-49,68-71` — emits `PydanticDeprecatedSince20`; a
  `pydantic>=2.0.0` floor bump to v3 would break class definition entirely.
- **`TransactionList`'s filter-summary text references `filters.category`/`filters.subcategory`, which no
  longer exist** — `frontend/src/components/TransactionList.jsx:161-165`,
  `frontend/src/context/TransactionContext.jsx:11-13` — cosmetic leftover from the pre-multi-select UI; the
  "in {category}" qualifier can never render (filtering itself works via `filters.categories`).
- **Three overlapping `.gitignore` files with copy-paste artifacts** — `.gitignore`, `backend/.gitignore`,
  `frontend/.gitignore` — cleanup only (secret coverage is correct); `frontend/.gitignore` carries
  backend/Python patterns that can never match from inside `frontend/`.

## 3. Gaps

Missing capabilities the app's purpose implies. Each verified-absent during the audit.

**User-facing:**

- **Per-transaction re-classification.** The only category-change path is `CategoryEditModal` → `addRule`,
  which is merchant-wide (and silently no-ops unless "create rule" is checked — the High finding). There is
  no API or UI to change a single transaction's category in isolation; `grep -rn "updateTransactionCategory"
  frontend/src` matches only a commented-out placeholder at `TransactionList.jsx:91`. Matters because
  one-off miscategorizations (or a legitimately different purchase from a normally-consistent merchant) can't
  be corrected without changing every transaction for that merchant.
- **Sync status / manual-sync control.** No sync-progress indicator, last-synced timestamp, or "sync now"
  button anywhere in `frontend/src`. Matters because sync happens invisibly inline with `GET /transactions`
  (Medium finding), so a slow first load is indistinguishable from a hang and the user can't force a refresh.
- **Month-over-month / trend comparison.** No comparison-across-periods view exists (`grep -rniE
  "month|trend|compar|history" frontend/src` finds only unrelated matches). Matters because comparing spend
  across periods is a core personal-finance question the app currently can't answer.
- **CSV / data export.** No download or export control anywhere (`grep -rniE "csv|export|download"
  frontend/src` finds only `export const`/`export default`). Matters because the user's own financial data is
  locked in a gitignored SQLite file with no supported way to get it out for taxes, spreadsheets, or backup.
- **Merchant search box.** Filtering is limited to the category dropdown and date range; no free-text merchant
  search (`grep -rniE "search" frontend/src` matches only `URLSearchParams`). Matters because finding all
  transactions for one merchant is a common lookup with no direct path today.
- **Original-currency display.** The backend carries `original_currency`, `original_amount`, `exchange_rate`,
  `exchange_rate_date` on `Transaction`, but the UI reads none of them and always formats JMD. Matters
  because — given the silent fallback-rate Medium finding — the user has no way to see the original USD amount
  or the rate applied, and thus no signal to question a bad conversion.

**Infrastructure (from gap candidates — inform Section 5 sequencing):**

- No database migration tooling (schema comes from `create_all()`, which never ALTERs existing tables).
- No backup/versioning for `classification_rules.json` or `transactions.db` (all user data in gitignored files).
- No secret-scanning / pre-commit guard despite live secrets in the working tree.
- No linting/formatting actually wired up (backend or frontend), despite README claims.
- No authentication layer to build on — adding auth is from-scratch, not a config flip.
- No structured observability around silent-failure paths (swallowed exceptions are currently invisible).
- No background job/queue for Gmail sync (every sync-triggering request pays full Gmail+OpenAI latency inline).
- No rate-limit/retry/cost guard around OpenAI classification (a large first sync fires many sequential calls).
- No atomic-write helper (temp-file + rename) anywhere JSON is persisted — the root of the corrupt-then-reset failure mode.

## 4. Recommended features (near-term, prioritized)

Personal-use, single-NCB-card scope only (multi-bank, mobile, predictions, and multi-currency are explicitly
out of scope). Prioritized by value ÷ effort; each names the files/pattern it builds on.

- [ ] **Per-transaction category override** (M) — highest value; also resolves the High "category edit
  silently discarded" bug. Build the missing `PATCH /transactions/{id}/category` endpoint and a
  `TransactionCrud.update_transaction_category`, then wire `services/api.js` +
  `CategoryEditModal.handleSubmit` + `TransactionList.handleCategoryUpdate` (currently a placeholder at
  `TransactionList.jsx:89-91`). Reuse the `update_category` bulk-update pattern in `category_rules_router.py`.
- [ ] **Merchant search box** (S) — high value, small. `merchant` is already indexed and `crud.py` already
  builds `ilike` patterns; add a `merchant` query param through `TransactionService.get_transactions` →
  `TransactionCrud.get_transactions`, expose it in `services/api.js`, and add an input to the filter row in
  `TransactionList.jsx`/`CategoryFilter.jsx`.
- [ ] **Original-currency display** (S) — small; addresses the conversion-trust gap. Parameterize
  `formatCurrency` in `utils/formatters.js` for currency, and render `original_amount`/`original_currency`/
  `exchange_rate` (already on `schemas.Transaction`) in the transaction row/detail. Also route
  `DeleteConfirmationModal.jsx:72` through `formatCurrency`.
- [ ] **Complete "top spending category"** (S/M) — the frontend half already exists (committed
  `TopSpendingCategory.jsx`). Add `top_spending_category`/`top_spending_category_amount` to
  `TransactionSummary` (`schemas.py:59-71`), compute them in `TransactionService.get_summary`
  (`transaction_service.py:99-138`, which already builds `by_primary_category`), then import and render the
  component in `App.jsx`.
- [ ] **Sync status + manual "Sync now"** (M) — high value; makes the sync-on-read latency livable.
  Expose the `sync_info` row (last-sync timestamp) and a `syncing` signal from a small endpoint, plus a
  manual-sync trigger, building on `SyncInfoModel`/`SyncInfoCrud` and `TransactionService`; add a control and
  indicator near `Header.jsx`/`DateRangePicker.jsx`.
- [ ] **CSV export of the current filtered view** (S) — moderate value, small effort. Reuse the existing
  filtered `GET /transactions` data; add either a client-side CSV blob download or a small
  `GET /transactions/export` endpoint, plus an export button in `TransactionList.jsx` and a call in
  `services/api.js`.
- [ ] **Month-over-month / trend view** (L) — high value, larger effort. Add a period-aggregation path
  (call `get_summary` per period or a new grouped aggregation in `crud.py`), a new API endpoint, and a new
  comparison component; the date/summary plumbing in `DateRangeContext`/`useSummary` is the closest existing anchor.

## 5. Suggested order of attack

1. **Lock down security first.** Restrict CORS to the known localhost origin(s) and add a minimal auth guard
   (even a shared token or localhost-only bind) — `main.py:38-44`, `dependencies.py`. Confirm the live secrets
   stay out of git and add a pre-commit secret scan (`backend/app/.env`, `credentials.json`, `token.json`).
2. **Fix the core-view correctness bugs.** Date-range end-of-day truncation (`DateRangeContext.jsx:87-91`) and
   category-edit-silently-discarded (`CategoryEditModal.jsx`/`TransactionList.jsx`) — the latter flows directly
   into building the per-transaction override feature.
3. **Fix data-integrity loss.** The `transaction_exists` dedup (Critical, `crud.py:108-114` — add a message-id
   or description signal) and the silent parse-failure + range-marked-synced path (`transaction_service.py:85-97`
   — count/surface failures and don't mark failed sub-ranges complete).
4. **Fix the visible-stat bugs.** `average_transaction` denominator (`transaction_service.py:133`) and
   `get_categories` multi-select (`crud.py:143-185`) — both small and high-visibility.
5. **Resolve the classifier split-brain** (`dependencies.py:12-41`) so rule edits take effect without a restart —
   unify on one classifier instance (or reload rules on mutation).
6. **Ship the top features:** per-transaction override, merchant search, and original-currency display (Section 4).
7. **Add sync visibility, then finish the extras:** sync status / manual sync, complete top-spending-category,
   CSV export.
8. **Pay down infra debt:** pin dependencies + add a lockfile, back up `classification_rules.json` and
   `transactions.db`, add an atomic-write helper, and plan the CRA→Vite migration.
