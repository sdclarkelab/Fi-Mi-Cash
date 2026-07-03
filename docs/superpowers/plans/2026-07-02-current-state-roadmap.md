# Current State & Roadmap Document Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce `docs/ROADMAP.md` — a self-contained current-state description, full severity-ranked issue audit, gap list, and prioritized near-term feature list for Fi-Mi-Cash.

**Architecture:** This is a documentation deliverable driven by an exhaustive code audit. Auditors read every backend and frontend source file, log verified findings into a shared findings file (`docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`), and a final task assembles `docs/ROADMAP.md` from those findings plus the spec. No application code is changed.

**Tech Stack:** Markdown, git. The audited app is FastAPI + SQLAlchemy + SQLite (`backend/app/`) and React 18 + CRA (`frontend/src/`). Read `CLAUDE.md` first for orientation.

**Spec:** `docs/superpowers/specs/2026-07-02-current-state-roadmap-design.md`

## Global Constraints

- **No code fixes.** The document is the sole deliverable. Do not modify any file under `backend/` or `frontend/`, even for obvious bugs.
- **Every claimed bug must be verified by reading the complete code path** — caller to callee — not by pattern-matching. If you cannot verify it, log it under "Unverified/rejected" in the findings file, not as a finding.
- **Every finding needs:** severity, `file:line` location, what is wrong, concrete impact.
- **Severity scale (from spec):** Critical = security or data-loss exposure; High = produces wrong results or breaks; Medium = reliability risk / architectural debt; Low = cleanup.
- **Features are near-term personal-use only** (single NCB-card user). Explicitly out of scope: multi-bank, mobile app, AI predictions, multi-currency.
- **Line numbers** must be from the current working tree on branch `address-tech-debt`.

## Findings file format

Every audit task appends to `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md` using exactly this entry format:

```markdown
### [SEVERITY] Short title
- **Location:** `path/to/file.py:123`
- **What:** One or two sentences describing the defect.
- **Impact:** What goes wrong for the user/data/security, concretely.
- **Verified:** How you confirmed it (e.g., "read full path: router -> service.get_summary -> line 133; excluded txs filtered at line 106 but len(transactions) at 133 counts them").
```

Gap and feature candidates discovered during audit go in `## Gap candidates` / `## Feature candidates` sections at the bottom of the findings file as one-line bullets.

---

### Task 1: Set up findings file; audit repo hygiene and secrets

**Files:**
- Create: `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`

**Interfaces:**
- Produces: the findings file with a coverage checklist that Tasks 2–4 tick off, and repo-level findings (secrets, gitignore, README drift).

- [ ] **Step 1: Create the findings file with the coverage checklist**

Write `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md` with this content (this checklist is the definitive list of files to audit; tick items as tasks complete):

```markdown
# Roadmap Audit Findings

Working notes for docs/ROADMAP.md. Entry format defined in
docs/superpowers/plans/2026-07-02-current-state-roadmap.md.

## Coverage checklist

### Repo level (Task 1)
- [ ] .gitignore, backend/.gitignore, frontend/.gitignore
- [ ] git ls-files check for secrets
- [ ] README.md claims vs reality
- [ ] backend/requirements.txt
- [ ] frontend/package.json

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

## Gap candidates

## Feature candidates

## Unverified/rejected
```

- [ ] **Step 2: Determine which secret files are actually tracked by git**

Run:

```bash
git ls-files backend/app | grep -E '\.env$|credentials\.json|token\.json|transactions\.db'
git log --oneline --diff-filter=A -- backend/app/credentials.json backend/app/token.json backend/app/.env backend/app/transactions.db
cat .gitignore backend/.gitignore 2>/dev/null | grep -E 'env|credentials|token|\.db'
```

Expected: this tells you whether `backend/app/.env` (contains a real OpenAI key), `credentials.json` (Google OAuth client secret), `token.json` (live Gmail token), and `transactions.db` (real financial data) are tracked, were ever committed (still in history even if since ignored), or are merely untracked working-tree files. Severity depends on the answer: tracked or in history = Critical (secrets in git history need rotation + history rewrite to fully fix); untracked-but-present = Medium (one bad `git add .` away, and `.env.example` sits beside them).

- [ ] **Step 3: Log repo-level findings**

Append findings entries (using the format above) for whatever Step 2 showed, plus these two known candidates after verifying them:

- README drift: `README.md` instructs `alembic upgrade head` but there is no alembic config anywhere (`find . -name alembic.ini -not -path '*/node_modules/*'` returns nothing); tables come from `Base.metadata.create_all()` in `backend/app/main.py:23`. It also documents `npm run lint` / `flake8` / env vars (`DATABASE_URL`, `ALLOWED_ORIGINS`, `.env.example` at repo root) that don't exist. Severity: Low (docs), but list each concrete mismatch.
- `backend/requirements.txt` has no version lockfile (only `>=` floors) and `frontend/package.json` pins `react-scripts 5.0.1` (CRA is deprecated/unmaintained). Severity: Low/Medium — judge after reading.

Tick the Task 1 coverage boxes.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md
git commit -m "docs: audit findings - repo hygiene and secrets"
```

---

### Task 2: Audit backend core (config, db, models)

**Files:**
- Modify: `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`

**Interfaces:**
- Consumes: findings file + entry format from Task 1.
- Produces: verified findings for the 10 "Backend core" files; architecture notes for ROADMAP Section 1 under a `## Architecture notes` heading you add to the findings file.

- [ ] **Step 1: Read all 10 backend-core files end-to-end**

Read every line of: `main.py`, `config.py`, `db/database.py`, `db/base_class.py`, `db/crud.py`, `models/transaction_model.py`, `models/sync_info_model.py`, `models/schemas.py`, `core/exceptions.py`, `core/logger.py` (all under `backend/app/`).

- [ ] **Step 2: Verify these known candidates and log them if confirmed**

- CORS: `backend/app/main.py:38-44` — `allow_origins=["*"]` together with `allow_credentials=True`. Impact: any website can call the API; there is no authentication on any endpoint, so any page the user visits could read their full transaction history while the backend runs. Severity: Critical (paired with no-auth finding).
- No authentication: no auth dependency anywhere (`grep -rn "Depends" backend/app/api` shows only service/db wiring; `SECRET_KEY`/`ACCESS_TOKEN_EXPIRE_MINUTES` in `config.py:13-14` are dead config). Severity: Critical.
- Hardcoded DB URL: `db/database.py:7` — `sqlite:///./transactions.db` is CWD-relative and not configurable; wrong CWD silently creates a fresh empty DB. Severity: Medium.
- Dead/duplicated settings: `config.py` — `SECRET_KEY` default `"your-secret-key-here"`; verify whether `CACHE_TTL`/`CACHE_MAX_SIZE` are actually used by the classifier's TTLCache or shadowed by literals. Severity: Low.

- [ ] **Step 3: Hunt for unknown issues in crud.py and models**

Specific things to check while reading (log whatever you actually confirm):
- `db/crud.py`: how filters compose (category/subcategory/multi-select JSON), whether `get_categories`/`get_transaction_count` duplicate filter logic that can drift from `get_transactions`; SQL injection is unlikely via ORM but check any raw string interpolation; check `transaction_exists` dedup criteria (what happens for two same-day same-merchant same-amount purchases — coffee twice in one day — is it dropped as duplicate?).
- `models/transaction_model.py` vs `models/schemas.py`: type mismatches (e.g., amounts stored as Float vs Decimal in Pydantic — float storage of money is a finding); `id` stored as string UUID; missing indexes on `date`/`merchant` used by every query.
- `models/schemas.py`: does `TransactionSummary` include `top_spending_category` fields that commit c4d2569 added? The untracked `TopSpendingCategory.jsx` reads `summary.top_spending_category` — confirm whether backend actually supplies it (WIP mismatch is a finding).

- [ ] **Step 4: Write architecture notes and commit**

Add `## Architecture notes` bullets sufficient for ROADMAP Section 1: request flow, sync-gap model (tables `transactions`, `sync_info`), where categories come from. Tick Task 2 coverage boxes.

```bash
git add docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md
git commit -m "docs: audit findings - backend core"
```

---

### Task 3: Audit backend services and API layer

**Files:**
- Modify: `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`

**Interfaces:**
- Consumes: findings file, Task 2's architecture notes.
- Produces: verified findings for the 7 "Backend services + API" files.

- [ ] **Step 1: Read all 7 files end-to-end**

`services/transaction_service.py`, `services/gmail_service.py`, `services/classifier_service.py`, `api/api_v1/dependencies.py`, `api/api_v1/routers/transactions_router.py`, `api/api_v1/routers/category_rules_router.py`, `data/classification_rules.json` (all under `backend/app/`).

- [ ] **Step 2: Verify these known candidates and log them if confirmed**

- Average bug: `services/transaction_service.py:133` — `average_transaction = sum(t.amount for t in included_transactions) / len(transactions)`. `included_transactions` filters out excluded transactions at line 106, but the divisor counts all. Impact: average is understated whenever any transaction is excluded. Severity: High.
- Sync-on-read blocking: `get_transactions` triggers Gmail fetch + one OpenAI call per new merchant inside the GET request. Impact: first request for a new date range can take tens of seconds and fails wholesale if Gmail/OpenAI is down; no way to see sync status. Severity: Medium (UX/reliability).
- Silent parse failures: `_parse_transaction` returns `None` on any exception or regex miss (`transaction_service.py:243-245,265-267`) and the email is never retried — the sync range is marked synced anyway (`_sync_transactions` records the range regardless). Impact: permanently missing transactions with only a log line. Severity: High.
- Hardcoded fallback FX rate: `transaction_service.py:182` — `Decimal('159')` when the currency API fails. Impact: silently wrong JMD amounts. Severity: Medium.
- Fragile email coupling: `_build_gmail_query` (`transaction_service.py:189`) hardcodes sender `no-reply-ncbcardalerts@jncb.com` and body-format regexes (`:209`, `:231`) parse NCB's HTML. A bank template change silently ends ingestion (combined with the silent-parse finding). Severity: Medium.
- Gmail token as pickle: `gmail_service.py` stores OAuth creds via `pickle` (`token.json` is actually a pickle); `flow.run_local_server` launches a browser from a server process. Severity: Low/Medium — judge after reading.
- Dependency wiring drift: `dependencies.py` — `get_gmail_service` is `@lru_cache`d but unused (`get_transaction_service` constructs a fresh `GmailService()` each request, line 25); a second module-level `_classifier` singleton duplicates `get_merchant_classifier` (lines 34-41). Verify which one `category_rules_router.py` uses; two classifier instances mean two rule caches that can disagree after a rule edit. Severity: depends on what you find — High if rule edits don't take effect until restart, else Low.
- Blocking I/O in async routes: Gmail client calls (`googleapiclient`) and OpenAI/classifier calls — check whether classifier uses async OpenAI client or blocks the event loop inside `async def` routes. Severity: Medium if blocking.

- [ ] **Step 3: Hunt for unknown issues**

While reading, specifically check: error handling in `category_rules_router.py` (does a rule update re-classify existing transactions via `TransactionService.update_category`, and does it update both the JSON file and the DB atomically?); `classifier_service.py` prompt/response parsing (what happens on malformed OpenAI JSON, does TTLCache use the config values, is there a cost/rate-limit guard?); duplicate-classification races when two requests sync simultaneously (SQLite + two `_sync_transactions` runs).

- [ ] **Step 4: Tick coverage boxes and commit**

```bash
git add docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md
git commit -m "docs: audit findings - backend services and API"
```

---

### Task 4: Audit frontend

**Files:**
- Modify: `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md`

**Interfaces:**
- Consumes: findings file; backend findings (to cross-check API contract mismatches).
- Produces: verified findings for all 23 frontend files; gap/feature candidates from the UI's perspective.

- [ ] **Step 1: Read all 23 frontend files end-to-end**

The full list is in the coverage checklist (Task 1, "Frontend" section). Includes the untracked `TopSpendingCategory.jsx`.

- [ ] **Step 2: Verify these known candidates and log them if confirmed**

- WIP integration: is `TopSpendingCategory.jsx` actually rendered anywhere (`grep -rn "TopSpendingCategory" frontend/src`)? Does the backend summary provide `top_spending_category` / `top_spending_category_amount` (cross-check with Task 2 Step 3 schema finding)? Log the WIP state either way — the ROADMAP must record what's half-done on this branch. Severity: informational/Low.
- Mixed HTTP clients: `services/api.js` uses axios (with an error interceptor) for transactions but raw `fetch` for the rules endpoints (lines 82-138) — two error-handling paths, interceptor doesn't cover rules. Severity: Low.
- Dead code: `hooks/useTransactions.js`, `hooks/useTransactionData.js`, `hooks/useSummary.js`, `context/CategoryContext.jsx` — check which are actually imported by anything (`grep -rn "useSummary\|useTransactionData\|CategoryContext" frontend/src`). Unused files mislead future work. Severity: Low.
- Currency display: `utils/formatters.js` — everything is stored in JMD after conversion; check the formatter hardcodes currency and how USD-original transactions display (does the UI show original USD amount and rate?). Severity: Low/gap.

- [ ] **Step 3: Hunt for unknown issues**

Check: pagination correctness (`Pagination.jsx` + `TransactionContext` — offset math, does count query share filters with list query?); date handling in `DateRangeContext` (timezone: `toISOString()` sends UTC — off-by-one-day risk for JMT (UTC-5) transactions near midnight, verify how backend compares dates); React Query cache keys (do mutations invalidate or just `refetch()`?); `AddTransactionModal` validation (can you submit a negative amount? non-numeric?); error states when backend is down.

- [ ] **Step 4: Record gap/feature candidates, tick coverage boxes, commit**

From the UI perspective, add to `## Gap candidates` at minimum (verify each is truly absent first): no per-transaction re-classification (only merchant-wide rules via `CategoryEditModal` — confirm), no sync status/manual-sync button, no month-over-month or any historical comparison view, no CSV/export, no search-by-merchant box. Then:

```bash
git add docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md
git commit -m "docs: audit findings - frontend"
```

---

### Task 5: Write docs/ROADMAP.md

**Files:**
- Create: `docs/ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md` (only to fix entries found deficient while writing)

**Interfaces:**
- Consumes: the complete findings file (all coverage boxes ticked, findings + gap/feature candidates + architecture notes).
- Produces: the final deliverable.

- [ ] **Step 1: Verify audit completeness**

Every box in the findings-file coverage checklist must be ticked. If any is not, stop and finish that task first. Every finding must have all four fields (Location/What/Impact/Verified) — fix any that don't.

- [ ] **Step 2: Write docs/ROADMAP.md with this exact skeleton**

```markdown
# Fi-Mi-Cash — Current State & Roadmap

> Audited 2026-07-02 on branch `address-tech-debt` (full backend + frontend
> read; method and raw notes in docs/superpowers/plans/). For dev setup and
> architecture-for-coding, see CLAUDE.md. This doc: what the app does, what's
> wrong, what's missing, what to build next.

## 1. Current State

### What it does today
[Feature inventory as user-visible capabilities, one bullet each: Gmail
sync of NCB card alerts; AI merchant categorization with editable rules;
date/category filtering; summaries by category/subcategory/card; manual
transactions; exclusion toggling; deletion of manual transactions;
pagination; USD->JMD conversion with historical rates.]

### How it works (behavior essentials)
[From the architecture notes: lazy sync-on-read with gap detection;
classification pipeline (rules file -> OpenAI -> TTL cache); single
GET /transactions response feeds the whole UI; data lives in SQLite.]

### Work in progress on this branch
[The top-spending-category state: what's committed, what's untracked,
whether backend and frontend halves match.]

## 2. Issues (full audit, 2026-07-02)

[One subsection per severity. Every entry: **title** — `file:line` —
impact sentence. Order within severity: most impactful first.]

### 🔴 Critical
### 🟠 High
### 🟡 Medium
### ⚪ Low

## 3. Gaps
[Missing capabilities the app's purpose implies. One bullet each with a
sentence on why it matters.]

## 4. Recommended features (near-term, prioritized)

[Ordered checklist. Each: - [ ] **Name** (S/M/L) — one-line why, one-line
implementation anchor (which existing files/pattern it builds on).]

## 5. Suggested order of attack
[Short numbered list interleaving fixes and features: secrets first, then
correctness bugs, then the top features. 5-8 items max.]
```

Fill every bracketed section from the findings file. Rules:
- Issues section: copy each finding's title, location, and impact — not the Verified field (that stays in the notes).
- Features: only near-term personal-use items (global constraint). Prioritize by (user value ÷ effort); S/M/L effort must name the files/pattern the estimate is based on.
- The doc must be self-contained per the spec's success criteria: a future session picks any item and starts work without re-deriving context.

- [ ] **Step 3: Self-check against spec success criteria**

From `docs/superpowers/specs/2026-07-02-current-state-roadmap-design.md`:
1. Every source file read — coverage checklist all ticked.
2. Every issue has verified `file:line` + impact — scan Section 2 for entries missing either.
3. Self-contained — read Section 4/5 cold: does each item say where in the code to start? Fix inline.

Also verify no application code was touched: `git status -- backend frontend` shows nothing staged/modified (the untracked `TopSpendingCategory.jsx` remains untracked).

- [ ] **Step 4: Commit**

```bash
git add docs/ROADMAP.md docs/superpowers/plans/2026-07-02-roadmap-audit-findings.md
git commit -m "docs: add current-state roadmap from full code audit"
```
