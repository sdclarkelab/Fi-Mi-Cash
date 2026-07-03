# Roadmap Audit Findings

Working notes for docs/ROADMAP.md. Entry format defined in
docs/superpowers/plans/2026-07-02-current-state-roadmap.md.

## Coverage checklist

### Repo level (Task 1)
- [x] .gitignore, backend/.gitignore, frontend/.gitignore
- [x] git ls-files check for secrets
- [x] README.md claims vs reality
- [x] backend/requirements.txt
- [x] frontend/package.json

### Backend core (Task 2)
- [x] backend/app/main.py
- [x] backend/app/config.py
- [x] backend/app/db/database.py
- [x] backend/app/db/base_class.py
- [x] backend/app/db/crud.py
- [x] backend/app/models/transaction_model.py
- [x] backend/app/models/sync_info_model.py
- [x] backend/app/models/schemas.py
- [x] backend/app/core/exceptions.py
- [x] backend/app/core/logger.py

### Backend services + API (Task 3)
- [ ] backend/app/services/transaction_service.py
- [ ] backend/app/services/gmail_service.py
- [ ] backend/app/services/classifier_service.py
- [ ] backend/app/api/api_v1/dependencies.py
- [ ] backend/app/api/api_v1/routers/transactions_router.py
- [ ] backend/app/api/api_v1/routers/category_rules_router.py
- [ ] backend/app/data/classification_rules.json

### Frontend (Task 4)
- [ ] frontend/src/App.jsx
- [ ] frontend/src/index.js
- [ ] frontend/src/services/api.js
- [ ] frontend/src/context/TransactionContext.jsx
- [ ] frontend/src/context/DateRangeContext.jsx
- [ ] frontend/src/context/CategoryContext.jsx
- [ ] frontend/src/hooks/useTransactions.js
- [ ] frontend/src/hooks/useTransactionData.js
- [ ] frontend/src/hooks/useSummary.js
- [ ] frontend/src/utils/formatters.js
- [ ] frontend/src/components/TransactionList.jsx
- [ ] frontend/src/components/TransactionSummary.jsx
- [ ] frontend/src/components/TopSpendingCategory.jsx (untracked WIP)
- [ ] frontend/src/components/CategoryFilter.jsx
- [ ] frontend/src/components/CategoryEditModal.jsx
- [ ] frontend/src/components/AddTransactionModal.jsx
- [ ] frontend/src/components/DeleteConfirmationModal.jsx
- [ ] frontend/src/components/DateRangePicker.jsx
- [ ] frontend/src/components/Pagination.jsx
- [ ] frontend/src/components/Header.jsx
- [ ] frontend/src/components/ErrorBoundary.jsx
- [ ] frontend/src/components/ErrorAlert.jsx
- [ ] frontend/src/components/LoadingSpinner.jsx

## Findings

### [Medium] Live secrets sit untracked in the working tree, one `git add -f` from exposure
- **Location:** `backend/app/.env`, `backend/app/credentials.json`, `backend/app/token.json`, `backend/app/transactions.db`
- **What:** A real OpenAI API key (132 chars, `sk-` prefix, confirmed non-placeholder), a Google OAuth client secret, a live Gmail token, and a SQLite DB of real financial transactions all live in the working tree. None is tracked and none was ever committed, but `.env.example` sits directly beside `.env` in the same directory, and the only protection is gitignore patterns.
- **Impact:** No leak today, but a single `git add -f`, a gitignore edit, or a tool that bypasses gitignore publishes a live API key, Gmail access, and real financial data. Severity is Medium per the audit scale (untracked-but-present); it would be Critical if tracked or in history.
- **Verified:** `git ls-files backend/app | grep -E '\.env$|credentials\.json|token\.json|transactions\.db'` returned nothing (exit 1); `git log --oneline --diff-filter=A -- backend/app/credentials.json backend/app/token.json backend/app/.env backend/app/transactions.db` empty; broader `git log --all --diff-filter=A -- '*.env' '*credentials.json' '*token.json' '*transactions.db'` also empty; `git status --ignored -- backend/app` lists all four under "Ignored files". Key shape checked via `awk` length/prefix test without printing the value.

### [Medium] `backend/app/data/classification_rules.json` is gitignored — category rules exist only on local disk
- **Location:** `backend/.gitignore` (last line: `/app/data/classification_rules.json`)
- **What:** The classifier's rules file — an app asset the API's category-rules router reads and writes — is explicitly gitignored, so it is not version controlled and has no backup.
- **Impact:** Disk loss or an accidental delete permanently loses all user-defined category rules; a fresh clone has no rules file at all. It is also a Task 3 audit target that exists only locally.
- **Verified:** `git ls-files backend/app/data/` returns nothing; `git status --ignored -- backend/app` lists `backend/app/data/`; `backend/.gitignore` final line is `/app/data/classification_rules.json`.

### [Medium] `backend/requirements.txt` has only `>=` floors and no lockfile
- **Location:** `backend/requirements.txt:1-12`
- **What:** All 12 dependencies use `>=` floors (e.g. `fastapi>=0.104.0`, `openai>=1.0.0`, `sqlalchemy>=2.0.0`); there is no lockfile of any kind in `backend/` (no `poetry.lock`, `Pipfile.lock`, or pinned requirements).
- **Impact:** Every fresh install resolves to whatever is newest, including future breaking majors; the environment is unreproducible and a reinstall can silently break the app.
- **Verified:** `cat backend/requirements.txt` — every line is a `>=` floor; `ls backend/*.lock backend/Pipfile.lock backend/poetry.lock` found no lockfiles.

### [Medium] Frontend is built on deprecated Create React App (`react-scripts 5.0.1`)
- **Location:** `frontend/package.json:17`
- **What:** `react-scripts` is pinned at `5.0.1` (last CRA release, 2022); CRA was officially deprecated by the React team in February 2025 and receives no maintenance.
- **Impact:** Transitive dependency vulnerabilities in the build toolchain will never be patched upstream; future React/tooling upgrades are blocked until migration (e.g. to Vite). `package-lock.json` exists, so installs are at least reproducible.
- **Verified:** `frontend/package.json:17` reads `"react-scripts": "5.0.1"`; scripts block (lines 25-30) is pure CRA (`react-scripts start/build/test/eject`); `frontend/package-lock.json` present.

### [Low] Three overlapping .gitignore files with copy-paste artifacts
- **Location:** `.gitignore`, `backend/.gitignore`, `frontend/.gitignore`
- **What:** Root, backend, and frontend gitignores redundantly repeat the same patterns (`.env*`, `*.db`, `credentials.json`, `token.json`, venv, `__pycache__`). `frontend/.gitignore` contains patterns that can never match from inside `frontend/` (`/frontend/node_modules`, `/backend/node_modules`, `/backend/dist`, `/frontend/.env`, Python patterns like `venv/` and `.pytest_cache/`).
- **Impact:** Cleanup only — coverage of the actual secret files is correct in all three; the drift just makes the ignore rules harder to reason about.
- **Verified:** Read all three files in full; confirmed the secret patterns appear in root and backend gitignores and that the frontend one carries backend/Python leftovers.

### [Low] README describes a project that doesn't exist: alembic, lint tooling, env vars, file layout
- **Location:** `README.md:98,106,132,150-158,181,201,241,243,277,282`
- **What:** Concrete mismatches, each verified against the tree:
  - `README.md:106` says run `alembic upgrade head`, but `find . -name alembic.ini -not -path '*/node_modules/*'` returns nothing; tables are actually created by `Base.metadata.create_all()` at `backend/app/main.py:23`.
  - `README.md:181,201` document a `/alembic` directory and `alembic.ini` in the project structure — neither exists.
  - `README.md:98` says `cp .env.example .env` at repo root — the only `.env.example` is at `backend/app/.env.example`; there is none at the root.
  - `README.md:132` says `cp .env.example .env.local` in `frontend/` — no `frontend/.env.example` exists.
  - `README.md:150-158` documents backend env vars `API_V1_PREFIX`, `DEBUG`, `SECRET_KEY`, `ALLOWED_ORIGINS`, `DATABASE_URL` — the real `backend/app/.env.example` has `OPENAI_API_KEY`, `GMAIL_CREDENTIALS_PATH`, `LOG_LEVEL`, `CACHE_TTL`, `CACHE_MAX_SIZE`.
  - `README.md:241,243` troubleshoot via `DATABASE_URL` and `ALLOWED_ORIGINS` — same nonexistent vars.
  - `README.md:277` says lint with `flake8` and `black --check` — neither is in `backend/requirements.txt` and there is no `setup.cfg`/`pyproject.toml`/`tox.ini`.
  - `README.md:282` says `npm run lint` — `frontend/package.json` scripts are only `start`/`build`/`test`/`eject`; README also claims "ESLint with Airbnb config" but `eslintConfig` extends `react-app`.
- **Impact:** A new user following the README hits a dead end at step 5 (`alembic` not installed, no config) and configures env vars the app never reads. Docs-only, so Low.
- **Verified:** Every bullet cross-checked with `grep -n` against `README.md`, `find` for alembic/`.env.example`, `cat backend/requirements.txt`, `cat backend/app/.env.example`, and `frontend/package.json` scripts/eslintConfig blocks.

### [Critical] No authentication on any endpoint
- **Location:** `backend/app/api/api_v1/routers/transactions_router.py`, `backend/app/api/api_v1/routers/category_rules_router.py`, `backend/app/api/api_v1/dependencies.py`
- **What:** No route declares an auth dependency. Every `Depends(...)` in the API layer wires a DB session, the transaction service, or the classifier — never a user/credential check. `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` are declared in `config.py:13-14` but are otherwise dead (see separate finding).
- **Impact:** Every endpoint — full transaction history, transaction creation/deletion, category-rule editing — is reachable by anyone who can reach the process, with zero identity or authorization checks.
- **Verified:** `grep -rnE "Depends|auth" backend/app/api` — all 15 matches are `Depends(get_db)`, `Depends(get_classifier)`, `Depends(get_transaction_service)` or the `fastapi` imports of `Depends`; none reference auth. Cross-checked `SECRET_KEY`/`ACCESS_TOKEN_EXPIRE_MINUTES` usage repo-wide: only defined in `config.py:13-14`, never read anywhere else (`grep -rnE "SECRET_KEY|ACCESS_TOKEN_EXPIRE" backend/app` returns only those two definition lines).

### [Critical] CORS allows any origin while allowing credentials
- **Location:** `backend/app/main.py:38-44`
- **What:** `CORSMiddleware` is configured with `allow_origins=["*"]`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]`. The `# TODO: Update this to only allow specific origins` comment on line 40 confirms this is known-temporary, not intentional.
- **Impact:** Combined with the no-auth finding above, any web page the user's browser visits (while the local backend is running) can issue cross-origin requests to the API and read the full transaction history or mutate/delete data — the browser's same-origin protections are explicitly disabled for this API.
- **Verified:** Read `backend/app/main.py:31-44` in full; the CORS middleware block is the only security-relevant middleware registered, and no auth middleware/dependency exists anywhere in the app (see previous finding).

### [High] `get_categories` silently ignores the multi-select `categories` filter that `get_transactions`/`get_transaction_count` both honor
- **Location:** `backend/app/db/crud.py:143-185`
- **What:** `TransactionCrud.get_categories` accepts a `categories: Optional[List[dict]] = None` parameter (line 147) identical to the one `get_transactions` (line 46) and `get_transaction_count` (line 191) use to build multi-select OR conditions — but the function body (lines 154-185) never references that parameter. It only applies `date_range`/`category`/`subcategory`/`min_confidence`/`include_excluded`. To make it worse, line 178 (`categories = {}`) reassigns the local name `categories` to the output accumulator, shadowing the ignored parameter, which hides the drift from anyone reading the function in isolation.
- **Impact:** `transaction_service.py:358-361` (`TransactionService.get_categories`) passes its `categories` argument straight through to this function (confirmed by grep), and `transactions_router.py:56` calls `service.get_categories(...)` to populate the category/subcategory list returned to the frontend's filter UI. When a user has an active multi-select category filter, the transaction list (via `get_transactions`) is correctly scoped, but the category dropdown (via this function) silently reverts to showing categories from the *entire* unfiltered dataset — a real, user-visible query-result inconsistency, not just a cosmetic issue.
- **Verified:** Read `crud.py:143-185` end-to-end and compared against the near-identical logic in `get_transactions` (43-106) and `get_transaction_count` (187-243), which both do implement the `categories` OR-condition block. Confirmed the caller chain with `grep -rn "get_categories" backend/app`: `transactions_router.py:56` → `transaction_service.py:358-361` → `crud.py:144` (TransactionCrud.get_categories), with `categories` forwarded unchanged at each hop.

### [High] `transaction_exists` dedup can silently drop a legitimate second same-day purchase
- **Location:** `backend/app/db/crud.py:108-114`
- **What:** `transaction_exists` treats a transaction as a duplicate solely on `(date == date) AND (amount == amount) AND (merchant == merchant)` — an exact equality match on all three fields, with no additional signal (e.g. description, email message ID, or sub-day time tolerance) to distinguish two independent purchases.
- **Impact:** `transaction_service.py:91` calls `TransactionCrud.transaction_exists(self.db, transaction)` during ingest and skips creating the transaction if it returns `True` (confirmed by grep). Two genuine purchases sharing merchant, amount, and date — e.g. buying coffee twice in one day for the same price at the same shop, or two identical subscription-adjacent charges — collapse to a single stored row; the second is silently discarded with no error or log, producing an under-reported spending total with no user-visible signal that anything was dropped. Severity note for roadmap triage: the High-vs-Critical call is close — silently dropping a real second purchase borders on data loss (the record is never stored, not merely misdisplayed); rated High because it destroys derived accuracy for a subset of transactions rather than exposing security or losing already-stored data, but Critical is defensible.
- **Verified:** Read `crud.py:108-114` for the exact filter predicate; confirmed the only caller and its skip-on-duplicate behavior via `grep -rn "transaction_exists" backend/app` → `transaction_service.py:91` (`if transaction and not TransactionCrud.transaction_exists(self.db, transaction):`).

### [Medium] Database URL is hardcoded and CWD-relative; wrong working directory silently creates a fresh empty DB
- **Location:** `backend/app/db/database.py:7-11`
- **What:** `SQLALCHEMY_DATABASE_URL = "sqlite:///./transactions.db"` is a module-level literal — not read from `Settings`/env — and the `./` path resolves against whatever the process's current working directory happens to be at import time. `config.py` has no `DATABASE_URL` field at all (the README documents one, but per Task 1's finding that env var is fictional).
- **Impact:** Launching the server from any directory other than the expected one doesn't error — SQLite plus `main.py:23`'s `Base.metadata.create_all(bind=engine)` silently create a brand-new empty `transactions.db` in that CWD, so the app comes up healthy-looking with zero transactions. The user sees all their data "gone" (it's still in the other file), and a subsequent Gmail sync can begin re-populating the wrong file, forking the dataset. Also blocks any deployment/config story (no way to point at another path or DB engine without editing source).
- **Verified:** Read `db/database.py:1-22` in full — the URL is a literal on line 7, engine built from it on lines 8-11, and the module imports nothing from `app.config`. Read `config.py:7-43` in full — no `DATABASE_URL`/DB-path setting exists. Confirmed the silent-creation path: `main.py:23` runs `create_all` on startup against whatever file the CWD-relative URL resolves to.

### [Medium] Money columns are declared `Numeric`/`Decimal` end-to-end but SQLite physically stores them as floating-point `REAL`
- **Location:** `backend/app/models/transaction_model.py:13,23,24` (`amount`, `original_amount`, `exchange_rate` as `Numeric(10,2)`/`Numeric(10,6)`); `backend/app/models/schemas.py:26,36,37` (`Decimal` fields in the `Transaction` Pydantic model)
- **What:** The declared types are correct (`Numeric`, not `Float`, contrary to the candidate hypothesis that literal `Float` columns store money) — but SQLite has no native decimal storage class. Verified empirically: creating an in-memory SQLite table with a `Numeric(10,2)` column, inserting `Decimal('19.99')`, `Decimal('0.10')`, `Decimal('0.20')` via SQLAlchemy, then running `select typeof(amount)` shows the storage class is `real` for every row, i.e. binary floating point, not an exact decimal representation.
- **Impact:** Reads through the SQLAlchemy ORM currently round-trip cleanly back to `Decimal` (SQLAlchemy converts via `str()` on read), so no incorrect totals were observed in this check. But the on-disk representation is IEEE-754 float: any raw SQL aggregation (`SUM`/`AVG` run directly against `transactions.db`, a future reporting script, or a DB-browser tool) operates on floats and is exposed to classic binary rounding error, and the precision guarantee implied by `Numeric(10,2)` is not actually enforced by the storage layer. This is a reliability/architecture risk rather than an observed-wrong-number-today bug, hence Medium not High.
- **Verified:** Ran `backend/.venv/bin/python` script creating an in-memory `sqlite:///:memory:` engine with a `Numeric(10,2)` column, inserting three `Decimal` values, and querying `typeof(amount)` via raw SQL — all three rows report storage class `real`. Cross-checked model declarations at `transaction_model.py:13-24` and schema declarations at `schemas.py:23-49`.

### [Medium] `TransactionSummary` schema has no `top_spending_category`/`top_spending_category_amount` fields the untracked frontend component expects
- **Location:** `backend/app/models/schemas.py:59-71` (`TransactionSummary`); `frontend/src/components/TopSpendingCategory.jsx:19-21,47-51` (untracked, not modified by this audit)
- **What:** `TransactionSummary` exposes `total_spending`, `transaction_count`, `average_transaction`, `by_primary_category`, `by_subcategory`, `by_card_type`, `merchants` — no `top_spending_category` or `top_spending_category_amount` field exists anywhere in the model. The untracked `TopSpendingCategory.jsx` reads `summary.top_spending_category` and `summary.top_spending_category_amount` directly off the `transaction_summary` object returned by the API.
- **Impact:** Not a live bug — the component is untracked, unwired dead code: nothing in `frontend/src` imports or renders `TopSpendingCategory`, so the running app is unaffected today. The defect is a WIP contract mismatch that blocks completing the feature: if the component were wired into the UI as-is, both fields would always be `undefined` on the object the backend returns, `hasTopCategory` (component lines 19-21) would always be falsy, and it would permanently render its "No Data" placeholder regardless of data (failing soft via the `&&` guard, not crashing). Finishing the feature requires the backend half — schema fields plus the computation — that was never implemented.
- **Verified:** Read `schemas.py:52-71` in full (`CategorySummary` and `TransactionSummary`) — no `top_spending_category` field present. `grep -rn "top_spending_category" backend/app` returns zero matches anywhere in the backend. Read `frontend/src/components/TopSpendingCategory.jsx` in full to confirm exactly which fields it reads and how the missing-field case degrades (falls through to the no-data branch, not a crash). Confirmed the component is unwired: `grep -rn "TopSpendingCategory" frontend/src` matches only the component's own file (its definition at line 7 and `export default` at line 58) — no importer exists.

### [Medium] `update_transactions_by_merchant` swallows every exception and returns 0, indistinguishable from "no rows matched"
- **Location:** `backend/app/db/crud.py:126-140`
- **What:** The bulk-update method wraps its `db.query(...).update(...)`/`db.commit()` in a bare `try/except Exception as e:` that rolls back and `return 0` on any failure — the caught exception `e` is never logged, re-raised, or surfaced in any way.
- **Impact:** A caller (e.g. the category-rules edit flow, which uses this to retroactively reclassify all transactions for a merchant) cannot distinguish "0 transactions matched this merchant" from "the update raised an exception and was silently rolled back" (e.g. a DB lock, constraint violation, or connection error). Real failures are masked as normal no-op results, making this class of bug effectively unobservable in logs.
- **Verified:** Read `crud.py:126-140` in full; confirmed no `logger` call (or any call) exists inside the `except` block, and `db/crud.py` never imports `app.core.logger` at all (only `app.config`, `app.models.schemas`, `app.models.sync_info_model`, `app.models.transaction_model`, `sqlalchemy` — confirmed via the file's import block at lines 1-11).

### [Low] Dead auth config: `SECRET_KEY`/`ACCESS_TOKEN_EXPIRE_MINUTES` defined but never consumed
- **Location:** `backend/app/config.py:13-14`
- **What:** `SECRET_KEY: str = "your-secret-key-here"` and `ACCESS_TOKEN_EXPIRE_MINUTES: int = 30` are declared on the `Settings` model but never read anywhere else in the codebase — there is no JWT/session code that consumes them.
- **Impact:** Low by itself (dead code, not a live vulnerability, since the value is never used to sign or verify anything) — but it's a red herring: it looks like auth exists when reading `config.py`, and reinforces the false impression addressed in the Critical no-auth finding above. If someone later wires it up without changing the default, the hardcoded literal `"your-secret-key-here"` would ship as a real secret.
- **Verified:** `grep -rnE "SECRET_KEY|ACCESS_TOKEN_EXPIRE" backend/app` returns only the two declaration lines (`config.py:13` and `config.py:14`); no other file references either name.

### [Low] Two separate `declarative_base()` objects exist; one is dead and unused
- **Location:** `backend/app/db/database.py:13` vs `backend/app/db/base_class.py:3`
- **What:** `db/database.py:13` defines its own `Base = declarative_base()`, completely separate from the `Base` defined in `db/base_class.py:3`. Every model (`transaction_model.py:5`, `sync_info_model.py:3`) and `main.py:10` import `Base` from `db.base_class`, not from `db.database`. `sync_info_model.py:3` even carries a comment — `# Import existing Base instead of creating a new one` — showing the duplication was already noticed once.
- **Impact:** No live bug today (nothing imports `database.Base`, confirmed by grep), but it's a landmine: if a future model or script imports `Base` from `db.database` instead of `db.base_class`, `Base.metadata.create_all()` in `main.py` (which uses `base_class.Base`) would never create that model's table, and the mismatch would be a confusing runtime-only bug (missing table, no error at import time).
- **Verified:** Read `database.py:1-13` and `base_class.py:1-3` side by side; `grep -rn "import Base" backend/app` shows all four import sites (`main.py:10`, `sync_info_model.py:3`, `transaction_model.py:5`) resolve to `app.db.base_class`, none to `app.db.database`.

### [Low] `Transaction`/`TransactionSummary` use Pydantic v1-style `class Config`, deprecated and warning under the installed Pydantic v2.9
- **Location:** `backend/app/models/schemas.py:46-49,68-71`
- **What:** Both models define a nested `class Config: json_encoders = {...}` — the Pydantic v1 configuration style. `backend/requirements.txt:4` pins `pydantic>=2.0.0`; the installed version in `backend/.venv` is 2.9.2, which supports `class Config` only via a deprecated compatibility shim (`model_config = ConfigDict(...)` is the v2-native replacement).
- **Impact:** Cleanup only today (no functional break), but confirmed to actively emit `PydanticDeprecatedSince20` at class-definition time under the installed version, and the shim is explicitly scheduled for removal in Pydantic v3 per the warning text — a routine `pydantic>=2.0.0` floor bump (see the existing "no lockfile" finding) could pull in v3 and break class definition entirely.
- **Verified:** Ran `backend/.venv/bin/python -c "import pydantic; print(pydantic.VERSION)"` → `2.9.2`. Reproduced the exact deprecation warning by defining an equivalent minimal model with `class Config: json_encoders = {...}` under `-W error::DeprecationWarning`: raised `pydantic.warnings.PydanticDeprecatedSince20: Support for class-based \`config\` is deprecated, use ConfigDict instead. ... Deprecated in Pydantic V2.0 to be removed in V3.0`.

## Architecture notes

- **Request flow:** `main.py` builds a single `FastAPI` app, registers `transactions_router` and `category_rules_router` under `settings.API_V1_STR` (`/api/v1`), and wires a single `CORSMiddleware`. A `lifespan` context manager runs `Base.metadata.create_all(bind=engine)` on startup — there is no migration tool; schema changes require a fresh DB file or manual ALTERs (consistent with Task 1's README-alembic finding).
- **Session/DI pattern:** `db/database.py` owns the SQLite engine (`sqlite:///./transactions.db`, CWD-relative, not env-configurable — see Medium finding above) and a `get_db()` generator that yields a `SessionLocal()` and closes it in a `finally` block; `api/api_v1/dependencies.py` exposes this as a FastAPI `Depends(get_db)` used to construct the service layer per-request.
- **Two declarative bases exist** (`db/base_class.py` and `db/database.py`); only `base_class.Base` is actually wired into models and `main.py`'s `create_all()` call (see Low finding above) — `database.Base` is inert dead code.
- **Sync-gap model:** two tables total — `transactions` (`TransactionModel`, one row per purchase, denormalized `primary_category`/`subcategory`/`card_type` as plain strings, `id` as a `String(36)` UUID) and `sync_info` (`SyncInfoModel`, a *single* row keyed `id="last_sync"` holding `last_sync_date`/`start_date`/`end_date`). `SyncInfoCrud.get_sync_gaps()` (crud.py:389-427) diffs a requested `DateRange` against the stored `(start_date, end_date)` to compute which sub-ranges still need fetching from Gmail (gap-before, gap-after), and `_calculate_optimal_sync_range`/`_apply_sync_limits` (crud.py:304-386) apply a sliding window bounded by `settings.MAX_SYNC_DAYS`/`SYNC_WINDOW_DAYS`/`MIN_SYNC_OVERLAP_HOURS` so the tracked range doesn't grow unbounded. Ingest-time dedup against already-stored transactions is a separate, simpler mechanism: `transaction_exists()` (crud.py:108-114), an exact `(date, amount, merchant)` match — see High finding on its collision risk.
- **Where categories come from:** there is no `categories` table. `primary_category`/`subcategory` are free-text columns set per-transaction (originally by the classifier service, out of this task's scope) and `get_categories()`/`get_transaction_count()` derive the distinct category→subcategory map and counts live from the `transactions` table by `SELECT DISTINCT`. Category *rules* (merchant → category/subcategory mappings used to drive future classification) are a completely separate, file-based store — `backend/app/data/classification_rules.json` (gitignored per Task 1's finding) — not modeled in the SQL schema at all.
- **Config surface:** `config.py`'s single `Settings(BaseSettings)` object is populated from `backend/app/.env` (`case_sensitive = True`). Confirmed-live fields: `API_V1_STR`, `PROJECT_NAME`, `OPENAI_API_KEY`, `GMAIL_CREDENTIALS_PATH`/`GMAIL_TOKEN_PATH`/`GMAIL_SCOPES`, `CACHE_TTL`/`CACHE_MAX_SIZE` (consumed by `classifier_service.py:125-126`'s `TTLCache`), `LOG_LEVEL` (consumed by `core/logger.py:13`), `MAX_SYNC_DAYS`/`SYNC_WINDOW_DAYS`/`MIN_SYNC_OVERLAP_HOURS` (consumed by the sync-gap logic above). Confirmed-dead fields: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES` (Low finding above). `MASTERCARD_TYPE`/`VISA_TYPE` are declared but not checked in this task's file set (consumer, if any, is in Task 3's scope).
- **Type boundary between layers:** `TransactionModel.id` is `String(36)` in the DB; `schemas.Transaction.id` is `uuid.UUID` in the API layer. Every `crud.py` call site does an explicit `str(transaction_id)` (write/filter) or accepts a `uuid.UUID` and stringifies it before querying — consistent throughout the file today, but there's no DB-level UUID type or CHECK constraint enforcing the format, so the consistency is a convention, not a guarantee.
- **Indexing:** contrary to one candidate hypothesis, `date`, `merchant`, `primary_category`, and `subcategory` all already carry `index=True` (`transaction_model.py:12,14-16`) — the columns actually used by every list/filter query in `crud.py` are indexed. No composite index exists for common combined filters (e.g. `date` + `primary_category` together), which SQLite's query planner can only partially exploit via single-column indexes, but this is a minor tuning note, not a missing-index defect.

## Gap candidates

- No database migration tooling at all (README's alembic is fictional); schema comes from `create_all()`, which never alters existing tables.
- No backup/versioning story for `classification_rules.json` or `transactions.db` — all user data lives in gitignored local files.
- No secret-scanning or pre-commit guard despite live secrets sitting in the working tree.
- No linting/formatting actually wired up (backend or frontend) despite README claims.
- No authentication layer of any kind exists to build on — adding auth is a from-scratch effort, not a config flip (see Critical findings).
- No structured logging/observability around silent-failure paths (e.g. `update_transactions_by_merchant`'s swallowed exceptions) — errors that should be loud are currently invisible.

## Feature candidates

- `top_spending_category`/`top_spending_category_amount` on `TransactionSummary`: the frontend half of this feature already exists (untracked `TopSpendingCategory.jsx`); the backend computation and schema fields are the missing half.

## Unverified/rejected

- **"Amounts stored as Float vs Decimal in Pydantic" (brief's Step 3 hypothesis), as literally stated — rejected.** `transaction_model.py:13,23` declares `amount`/`original_amount` as `Numeric(10,2)` (not `Float`), and `schemas.py:26,36` declares them as `Decimal` in Pydantic — the two layers agree on type. The real, different issue (SQLite physically storing `Numeric` as floating-point `REAL`) is logged above as its own Medium finding instead.
- **"Missing indexes on date/merchant used by every query" — rejected.** `transaction_model.py:12,14` shows `date = Column(DateTime, index=True)` and `merchant = Column(String, index=True)`; `primary_category`/`subcategory` are also indexed (lines 15-16). All four are indexed already; see the Indexing architecture note above for the (minor) composite-index nuance.
- **"CACHE_TTL/CACHE_MAX_SIZE shadowed by literals" — rejected.** `grep -rnE "CACHE_TTL|CACHE_MAX_SIZE" backend/app` shows both are read by `classifier_service.py:125-126` (`TTLCache(maxsize=settings.CACHE_MAX_SIZE, ttl=settings.CACHE_TTL)`) — genuinely wired to config, not shadowed by hardcoded literals. (`classifier_service.py` itself is Task 3's file; confirmed here only via grep for the config-consumption cross-check, not read end-to-end.)
- **`id` as `String(36)` vs Pydantic `uuid.UUID` — investigated, not logged as a bug.** Every `crud.py` call site (`create_transaction`, `get_transaction_by_id`, `set_exclusion`, `delete_transaction`) consistently converts with `str()`/accepts `uuid.UUID` before querying; no call site was found that compares raw types without conversion. Logged as an architecture note (type-boundary convention, not a guarantee) rather than a finding, since no actual defect was observed within this task's file set.
- **SQL injection via `ilike(f"%{cat_name}%")` in `crud.py:72-84,216-228` — checked, not a vulnerability.** The f-string only builds the `LIKE` pattern text; it is passed to SQLAlchemy's `.ilike()` as a bound parameter, not interpolated into raw SQL. A user-supplied `%`/`_` could broaden their own match unexpectedly (wildcard-injection, cosmetic) but this is not a security defect and wasn't logged as one.
