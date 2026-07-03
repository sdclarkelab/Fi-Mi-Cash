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
- [ ] backend/app/main.py
- [ ] backend/app/config.py
- [ ] backend/app/db/database.py
- [ ] backend/app/db/base_class.py
- [ ] backend/app/db/crud.py
- [ ] backend/app/models/transaction_model.py
- [ ] backend/app/models/sync_info_model.py
- [ ] backend/app/models/schemas.py
- [ ] backend/app/core/exceptions.py
- [ ] backend/app/core/logger.py

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

## Gap candidates

- No database migration tooling at all (README's alembic is fictional); schema comes from `create_all()`, which never alters existing tables.
- No backup/versioning story for `classification_rules.json` or `transactions.db` — all user data lives in gitignored local files.
- No secret-scanning or pre-commit guard despite live secrets sitting in the working tree.
- No linting/formatting actually wired up (backend or frontend) despite README claims.

## Feature candidates

## Unverified/rejected
