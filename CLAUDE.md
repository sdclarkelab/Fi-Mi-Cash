# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Fi-Mi-Cash is a personal finance app that syncs bank transaction emails from Gmail, categorizes merchants with OpenAI, and shows spending analytics. Two independent apps in one repo: a FastAPI backend (`backend/`) and a Create React App frontend (`frontend/`).

## Commands

### Backend (Python/FastAPI)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # .venv already exists locally
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend tests: `cd backend && .venv/bin/python -m pytest tests -v` (dev deps: `pip install -r requirements-dev.txt`). There are no alembic migrations (despite what README.md says — tables are created via `Base.metadata.create_all()` at startup, followed by the small additive migrations in `backend/app/db/migrations.py`) and no configured linter.

**Working directory matters**: `.env`, `transactions.db`, `token.json`, `credentials.json`, and `GMAIL_TOKEN_PATH` are all resolved relative to the process CWD. The existing runtime files live in `backend/app/`, so the server has historically been run with that as the working directory (PyCharm run config). If the app starts but can't find settings or creates a fresh empty DB, check the CWD first.

Required env vars (see `backend/app/.env.example`): `OPENAI_API_KEY`, `GMAIL_CREDENTIALS_PATH`, `API_KEY`. The frontend must send the same key: set `REACT_APP_API_KEY` in `frontend/.env` to the identical value (see `frontend/.env.example`). All API routes under `/api/v1` require the `X-API-Key` header; `/docs` stays open. Always bind the server to 127.0.0.1 (the PyCharm run config too) — CORS only admits `http://localhost:3000` / `http://127.0.0.1:3000`. First run triggers an interactive Google OAuth flow in the browser and pickles the token to `token.json`.

### Frontend (React 18 + CRA)

```bash
cd frontend
npm install
npm start          # dev server on :3000, expects backend on :8000
npm test           # Jest via react-scripts (watch mode); npm test -- --watchAll=false for one-shot
npm test -- -t "name"   # single test
npm run build
```

`REACT_APP_API_BASE_URL` (in `frontend/.env`) points at the backend, default `http://localhost:8000/api/v1`.

## Architecture

### Backend flow — lazy Gmail sync

The core design: transactions are **pulled from Gmail lazily on read**. `GET /api/v1/transactions` → `TransactionService.get_transactions()` first checks `SyncInfoCrud.get_sync_gaps()` for date sub-ranges not yet synced, fetches only those gaps from Gmail, parses each email into a transaction (regex parse + AI categorization), stores them in SQLite, records the synced range in the `sync_info` table, then serves the query from the DB. Sync windowing is tuned by `MAX_SYNC_DAYS` / `SYNC_WINDOW_DAYS` / `MIN_SYNC_OVERLAP_HOURS` in `app/config.py`.

Layering in `backend/app/`:

- `api/api_v1/routers/` — `transactions_router.py` (list/count/create/delete/toggle-exclude), `category_rules_router.py` (CRUD for classification rules), and `sync_router.py` (sync status + manual force-sync). Wired in `main.py` under `/api/v1`.
- `api/api_v1/dependencies.py` — DI: builds `TransactionService(GmailService, MerchantClassifier, db)` per request; the classifier is a cached singleton.
- `services/` — the meat:
  - `transaction_service.py` — orchestrates sync, email parsing, filtering, and computes `TransactionSummary` (per-category, per-subcategory, per-card-type aggregates) in Python, not SQL.
  - `gmail_service.py` — Google OAuth + Gmail search/fetch. Emails are matched with a Gmail query built from the bank's alert format (card types configured in `config.py`: NCB Visa/Mastercard, Jamaican bank).
  - `classifier_service.py` — merchant → (category, subcategory, confidence). Checks `SpecialClassificationRuleManager` rules first (persisted to `app/data/classification_rules.json`), falls back to OpenAI, caches results in a TTLCache.
- `db/` — SQLAlchemy against SQLite (`crud.py` holds all queries as static methods on `TransactionCrud` / `SyncInfoCrud`); `models/` — SQLAlchemy models (`transaction_model.py`, `sync_info_model.py`) and all Pydantic schemas in `schemas.py`.

Transactions carry `excluded` (kept in results but omitted from summaries), `source` (`"email"` vs manual), `card_type`, and original-currency/exchange-rate fields for USD conversions.

### Category filtering — two formats

Multi-select filters are sent as repeated `categories` query params, each a **JSON-encoded** `{category, subcategory}` object; the router `json.loads` each one. The older single `category`/`subcategory` params still work as a fallback. `frontend/src/services/api.js` implements the client side of both.

### Frontend structure

Single-page app, no router. State flows through three contexts (`src/context/`): `DateRangeContext` and `CategoryContext` hold filter state; `TransactionContext` wraps a React Query fetch keyed on those filters and exposes `transactionData` + `refetch` to everything else. One `GET /transactions` call returns transactions, summary, and the category tree together; components (`TransactionList`, `TransactionSummary`, `CategoryFilter`, modals) all read from the context rather than fetching independently. After mutations (create/delete/toggle-exclude, done via `src/services/api.js`), components call `refetch()`.

## Git hooks

One-time setup per clone: `git config core.hooksPath .githooks`. The pre-commit hook blocks staging of secret files (`.env`, `credentials.json`, `token.json`, `*.db`, `classification_rules.json`) and runs `gitleaks` (install: `brew install gitleaks`) on staged content.
