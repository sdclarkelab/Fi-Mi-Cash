# Security Lockdown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the two Critical audit findings — no auth and wildcard CORS — with an `X-API-Key` guard on every API route plus a localhost-only CORS policy, and add a pre-commit hook that blocks committing the live secrets.

**Architecture:** A required `API_KEY` setting and a `verify_api_key` FastAPI dependency applied at router-include time in `main.py`; CORS origins move from `["*"]` to a `CORS_ORIGINS` setting defaulting to the two localhost:3000 origins. The React frontend sends the key from `REACT_APP_API_KEY` on its axios instance and its raw-`fetch` rules calls. A tracked `.githooks/pre-commit` script path-blocks known secret files and runs gitleaks content scanning.

**Tech Stack:** FastAPI (`APIKeyHeader`), pytest + `TestClient` (httpx already in the venv), React/axios/Jest, gitleaks via Homebrew.

**Spec:** `docs/superpowers/specs/2026-07-03-security-lockdown-design.md`

## Global Constraints

- Header name is exactly `X-API-Key`; backend env var `API_KEY`; frontend env var `REACT_APP_API_KEY`.
- Missing/wrong key → HTTP **401** with detail `"Invalid or missing API key"`.
- CORS default origins: `["http://localhost:3000", "http://127.0.0.1:3000"]`; `allow_credentials=False`.
- `/docs` and `/api/v1/openapi.json` stay unauthenticated.
- Backend commands run from `backend/` using the existing venv: `.venv/bin/python -m pytest ...`. Frontend commands run from `frontend/`.
- Never stage or commit: `backend/app/.env`, `frontend/.env`, `credentials.json`, `token.json`, `*.db`, `classification_rules.json`. (Local edits to the `.env` files are expected; commits of them are not.)
- Only new dependency: `pytest` (dev-only, in a new `requirements-dev.txt`). No new runtime deps.

---

### Task 1: Backend API-key guard + CORS restriction

**Files:**
- Create: `backend/requirements-dev.txt`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Modify: `backend/app/config.py` (lines 12–14, add CORS setting)
- Modify: `backend/app/api/api_v1/dependencies.py` (add `verify_api_key`)
- Modify: `backend/app/main.py:37-53` (CORS block, router includes, `__main__` bind)
- Modify: `backend/app/.env.example` (add `API_KEY=`)
- Modify (local, untracked — do NOT commit): `backend/app/.env` (add real `API_KEY`)

**Interfaces:**
- Consumes: existing `get_settings()` (`app/config.py`), routers in `app/api/api_v1/routers/`.
- Produces: `verify_api_key(api_key: str | None) -> None` dependency in `app.api.api_v1.dependencies` (raises `HTTPException(401)`); `Settings.API_KEY: str` (required) and `Settings.CORS_ORIGINS: List[str]`. Task 2 relies on header name `X-API-Key` and the 401 contract.

- [ ] **Step 1: Add dev requirements and install**

Create `backend/requirements-dev.txt`:

```
-r requirements.txt
pytest>=8.0.0
httpx>=0.27.0
```

Run: `cd backend && .venv/bin/pip install -r requirements-dev.txt`
Expected: pytest installs; everything else already satisfied.

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/conftest.py`. Settings load from a CWD-relative `.env` (which doesn't exist in `backend/`), so these env vars fully determine test config. They must be set **before** `app.main` is imported (conftest top-level runs first):

```python
import os

# Must be set before app.main is imported: Settings has required fields
# and get_settings() is lru_cached at first call.
os.environ["API_KEY"] = "test-api-key"
os.environ["OPENAI_API_KEY"] = "test-openai-key"
os.environ["GMAIL_CREDENTIALS_PATH"] = "credentials.json"
```

Create `backend/tests/test_auth.py`. It uses `GET /api/v1/rules` (the lightest route) with `get_classifier` overridden so no rules file, DB, or network is touched:

```python
from fastapi.testclient import TestClient

from app.api.api_v1.dependencies import get_classifier, verify_api_key  # noqa: F401
from app.main import app


class StubRuleManager:
    def get_all_rules(self):
        return []


class StubClassifier:
    rule_manager = StubRuleManager()


app.dependency_overrides[get_classifier] = lambda: StubClassifier()

client = TestClient(app)


def test_missing_api_key_rejected():
    response = client.get("/api/v1/rules")
    assert response.status_code == 401


def test_wrong_api_key_rejected():
    response = client.get("/api/v1/rules", headers={"X-API-Key": "wrong-key"})
    assert response.status_code == 401


def test_correct_api_key_accepted():
    response = client.get("/api/v1/rules", headers={"X-API-Key": "test-api-key"})
    assert response.status_code == 200
    assert response.json() == {"rules": []}


def test_openapi_stays_open():
    response = client.get("/api/v1/openapi.json")
    assert response.status_code == 200


def test_cors_allows_frontend_origin():
    response = client.options(
        "/api/v1/transactions",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_blocks_unknown_origin():
    response = client.options(
        "/api/v1/transactions",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert "access-control-allow-origin" not in response.headers
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd backend && .venv/bin/python -m pytest tests/test_auth.py -v`
Expected: collection error — `ImportError: cannot import name 'verify_api_key'`. (If instead you see a `ValidationError` about `API_KEY`, conftest env setup isn't running first — fix that before proceeding.)

- [ ] **Step 4: Implement settings changes**

In `backend/app/config.py`, replace the dead auth settings (lines 12–14):

```python
    # Authentication
    SECRET_KEY: str = "your-secret-key-here"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
```

with:

```python
    # Authentication — shared secret required on every API request (X-API-Key header)
    API_KEY: str

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
```

(`List` is already imported in this file.)

- [ ] **Step 5: Implement `verify_api_key`**

In `backend/app/api/api_v1/dependencies.py`, add to the imports:

```python
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.config import get_settings
```

(Keep the existing imports; only `Depends` is already there — extend that line.)

Then add at module level, after the imports:

```python
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def verify_api_key(api_key: str = Security(_api_key_header)) -> None:
    settings = get_settings()
    if api_key is None or not secrets.compare_digest(api_key, settings.API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
```

- [ ] **Step 6: Wire CORS + guard in `main.py`**

In `backend/app/main.py`:

Change the fastapi import (line 3) to:

```python
from fastapi import Depends, FastAPI
```

Add to the app imports:

```python
from app.api.api_v1.dependencies import verify_api_key
```

Replace the CORS block and router includes (lines 37–48):

```python
# CORS: only the local frontend may call this API from a browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router — every route requires the X-API-Key header
app.include_router(
    transactions_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)
app.include_router(
    category_rules_router,
    prefix=settings.API_V1_STR,
    dependencies=[Depends(verify_api_key)],
)
```

And in the `__main__` block, change `host="0.0.0.0"` to `host="127.0.0.1"`.

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd backend && .venv/bin/python -m pytest tests/test_auth.py -v`
Expected: all 6 tests PASS.

- [ ] **Step 8: Generate the real key and update env files**

Generate a key: `cd backend && .venv/bin/python -c "import secrets; print(secrets.token_urlsafe(32))"`

Append to `backend/app/.env` (local file — do NOT stage/commit):

```
API_KEY=<generated value>
```

Append to `backend/app/.env.example`:

```
API_KEY=generate_with_python_secrets_token_urlsafe
```

- [ ] **Step 9: Commit**

```bash
git add backend/requirements-dev.txt backend/tests/conftest.py backend/tests/test_auth.py backend/app/config.py backend/app/api/api_v1/dependencies.py backend/app/main.py backend/app/.env.example
git commit -m "feat: require X-API-Key on all API routes; restrict CORS to localhost

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Verify `git status` afterwards shows `backend/app/.env` still untracked.

---

### Task 2: Frontend sends the API key

**Files:**
- Modify: `frontend/src/services/api.js`
- Create: `frontend/src/services/api.test.js`
- Create: `frontend/.env.example`
- Modify (local, untracked — do NOT commit): `frontend/.env` (add `REACT_APP_API_KEY`)

**Interfaces:**
- Consumes: header name `X-API-Key` and env var contract from Task 1; the same key value written to `backend/app/.env` in Task 1 Step 8.
- Produces: new named export `api` (the axios instance) from `frontend/src/services/api.js`; all existing exported functions now send `X-API-Key`.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/services/api.test.js`:

```javascript
describe("API key header", () => {
  const originalFetch = global.fetch;
  const originalKey = process.env.REACT_APP_API_KEY;

  beforeEach(() => {
    jest.resetModules();
    process.env.REACT_APP_API_KEY = "test-key";
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ rules: [] }),
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    process.env.REACT_APP_API_KEY = originalKey;
  });

  it("sets X-API-Key as an axios default header", () => {
    const { api } = require("./api");
    expect(api.defaults.headers["X-API-Key"]).toBe("test-key");
  });

  it("sends X-API-Key on rules fetch requests", async () => {
    const { getAllRules } = require("./api");
    await getAllRules();
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rules"),
      expect.objectContaining({
        headers: expect.objectContaining({ "X-API-Key": "test-key" }),
      })
    );
  });

  it("sends X-API-Key on rule delete requests", async () => {
    const { deleteRule } = require("./api");
    await deleteRule("Some Merchant");
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/rules/"),
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({ "X-API-Key": "test-key" }),
      })
    );
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npm test -- --watchAll=false api.test.js`
Expected: FAIL — `api` is not exported (undefined), and the fetch calls are made without a headers option containing `X-API-Key`.

- [ ] **Step 3: Implement in `api.js`**

In `frontend/src/services/api.js`:

Replace lines 3–11 with:

```javascript
const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api/v1";

const API_KEY = process.env.REACT_APP_API_KEY;

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY,
  },
});
```

In `getAllRules`, replace the fetch call with:

```javascript
  const response = await fetch(`${API_BASE_URL}/rules`, {
    headers: { "X-API-Key": API_KEY },
  });
```

In `addRule` and `updateRule`, extend the headers object to:

```javascript
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
```

In `deleteRule`, replace the options object with:

```javascript
    {
      method: "DELETE",
      headers: { "X-API-Key": API_KEY },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npm test -- --watchAll=false api.test.js`
Expected: 3 tests PASS.

Also run the full suite to check for regressions: `cd frontend && npm test -- --watchAll=false`
Expected: no new failures (note: pre-existing failures, if any, are out of scope — record them, don't fix them).

- [ ] **Step 5: Update env files**

Append to `frontend/.env` (local file — do NOT stage/commit) the same key value generated in Task 1 Step 8:

```
REACT_APP_API_KEY=<same value as backend API_KEY>
```

Create `frontend/.env.example`:

```
REACT_APP_API_BASE_URL=http://localhost:8000/api/v1
REACT_APP_API_KEY=must_match_backend_API_KEY
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/services/api.js frontend/src/services/api.test.js frontend/.env.example
git commit -m "feat: send X-API-Key header from frontend API client

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Verify `git status` afterwards shows `frontend/.env` untracked.

---

### Task 3: Pre-commit secret scan (gitleaks + tracked hook)

**Files:**
- Create: `.githooks/pre-commit` (executable)
- Local config: `git config core.hooksPath .githooks`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: a pre-commit hook active for all future commits in this repo clone. Task 4 documents the setup.

- [ ] **Step 1: Install gitleaks and check its CLI generation**

Run: `brew install gitleaks && gitleaks version`
Expected: installs and prints a version (8.x).

Run: `gitleaks git --help >/dev/null 2>&1 && echo NEW_CLI || echo OLD_CLI`
Expected: `NEW_CLI` on current Homebrew versions (≥ 8.19). If `OLD_CLI`, use the alternate command noted in Step 2.

- [ ] **Step 2: Create the hook script**

Create `.githooks/pre-commit`:

```bash
#!/usr/bin/env bash
# Pre-commit guard for Fi-Mi-Cash: live secrets sit untracked in the working
# tree (.env, credentials.json, token.json, transactions.db, rules JSON).
# Layer 1 blocks them by path even under `git add -f`; layer 2 runs gitleaks
# content scanning on everything staged.
set -euo pipefail

blocked_pattern='(^|/)\.env$|(^|/)credentials\.json$|(^|/)token\.json$|\.db$|(^|/)classification_rules\.json$'

staged_files=$(git diff --cached --name-only --diff-filter=ACMR)

if matches=$(printf '%s\n' "$staged_files" | grep -E "$blocked_pattern"); then
    echo "COMMIT BLOCKED: sensitive file(s) staged:" >&2
    printf '%s\n' "$matches" >&2
    echo "Unstage with: git reset -- <file>" >&2
    exit 1
fi

if command -v gitleaks >/dev/null 2>&1; then
    gitleaks git --pre-commit --staged --redact
else
    echo "WARNING: gitleaks not installed (brew install gitleaks); content scan skipped." >&2
fi
```

If Step 1 reported `OLD_CLI`, use `gitleaks protect --staged --redact` instead of the `gitleaks git` line.

Make it executable and activate it:

```bash
chmod +x .githooks/pre-commit
git config core.hooksPath .githooks
```

- [ ] **Step 3: Test — path-based block catches a forced add**

```bash
cd /Users/sclarke/Projects/Fi-Mi-Cash
touch fake-test.db
git add -f fake-test.db
.githooks/pre-commit; echo "exit: $?"
```

Expected: prints `COMMIT BLOCKED: sensitive file(s) staged:` with `fake-test.db`, `exit: 1`.

Clean up: `git reset -- fake-test.db && rm fake-test.db`

- [ ] **Step 4: Test — gitleaks catches secret content**

```bash
printf 'token = "ghp_0123456789abcdefghijklmnopqrstuvwxyz"\n' > leak-test.txt
git add leak-test.txt
.githooks/pre-commit; echo "exit: $?"
```

Expected: gitleaks reports a finding (redacted), `exit: 1`.

Clean up: `git reset -- leak-test.txt && rm leak-test.txt`

- [ ] **Step 5: Test — the real secrets are caught by the path guard**

```bash
git add -f backend/app/.env
.githooks/pre-commit; echo "exit: $?"
git reset -- backend/app/.env
```

Expected: `COMMIT BLOCKED` listing `backend/app/.env`, `exit: 1`, then unstaged.

- [ ] **Step 6: Commit the hook (this also proves a clean commit passes)**

```bash
git add .githooks/pre-commit
git commit -m "chore: add pre-commit hook blocking secret files + gitleaks scan

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Expected: the hook runs during this commit and passes.

---

### Task 4: End-to-end verification + docs

**Files:**
- Modify: `CLAUDE.md` (currently untracked — this task commits it; it is the project-instructions file meant to be checked in)

**Interfaces:**
- Consumes: everything from Tasks 1–3 (running guard, keys in both `.env` files, active hook).
- Produces: verified working system + setup docs.

- [ ] **Step 1: Boot the backend and verify the guard live**

The CWD must be `backend/app/` (that's where `.env`, `token.json`, and `transactions.db` live — see CLAUDE.md), but the `app` package root is `backend/`, so `PYTHONPATH=..` is required when launching from the CLI:

```bash
cd backend/app && PYTHONPATH=.. ../.venv/bin/python -m uvicorn app.main:app --port 8000 --host 127.0.0.1
```

Expected: startup logs "Starting up Transaction API" with no validation error (proves `API_KEY` is being read from `backend/app/.env`).

- [ ] **Step 2: Curl checks**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/api/v1/rules
# Expected: 401

curl -s -o /dev/null -w "%{http_code}\n" -H "X-API-Key: $(grep '^API_KEY=' backend/app/.env | cut -d= -f2-)" http://127.0.0.1:8000/api/v1/rules
# Expected: 200

curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/docs
# Expected: 200 (docs stay open)
```

Stop the server afterwards.

- [ ] **Step 3: Frontend smoke check**

Run: `cd frontend && npm start`, open http://localhost:3000, confirm transactions load (no 401 errors in the browser console / network tab). This confirms the key matches end-to-end. Then stop the dev server.

If running non-interactively: `curl` the CRA dev server is insufficient to prove this — ask the user to confirm the UI loads, or verify with the project's run/verify tooling.

- [ ] **Step 4: Document setup in CLAUDE.md**

Add to `CLAUDE.md`, in the Backend commands section after the env-vars paragraph:

```markdown
Required env vars (see `backend/app/.env.example`): `OPENAI_API_KEY`, `GMAIL_CREDENTIALS_PATH`, `API_KEY`. The frontend must send the same key: set `REACT_APP_API_KEY` in `frontend/.env` to the identical value (see `frontend/.env.example`). All API routes under `/api/v1` require the `X-API-Key` header; `/docs` stays open. Always bind the server to 127.0.0.1 (the PyCharm run config too) — CORS only admits `http://localhost:3000` / `http://127.0.0.1:3000`.
```

(Replace the existing "Required env vars" sentence rather than duplicating it.)

Add a new top-level section near the end:

```markdown
## Git hooks

One-time setup per clone: `git config core.hooksPath .githooks`. The pre-commit hook blocks staging of secret files (`.env`, `credentials.json`, `token.json`, `*.db`, `classification_rules.json`) and runs `gitleaks` (install: `brew install gitleaks`) on staged content.
```

Backend tests note — in the backend commands section, replace the "There are no backend tests" sentence with:

```markdown
Backend tests: `cd backend && .venv/bin/python -m pytest tests -v` (dev deps: `pip install -r requirements-dev.txt`). There are no alembic migrations (despite what README.md says — tables are created via `Base.metadata.create_all()` at startup) and no configured linter.
```

- [ ] **Step 5: Run the full backend test suite one last time**

Run: `cd backend && .venv/bin/python -m pytest tests -v`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: document API key setup, git hooks, and backend tests in CLAUDE.md

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

Note: CLAUDE.md was untracked before this commit; this intentionally checks it in (it self-describes as "checked into the codebase").
