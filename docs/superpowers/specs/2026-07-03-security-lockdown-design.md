# Security Lockdown — Design

**Date:** 2026-07-03
**Source:** docs/ROADMAP.md §5 item 1 ("Lock down security first")
**Scope:** CORS restriction, minimal API-key auth, pre-commit secret scan.
Out of scope: login/JWT auth, rate limiting, the other roadmap items.

## Goal

Close the two Critical audit findings (no auth on any endpoint; CORS `*` with
credentials) and guard the untracked live secrets (`backend/app/.env`,
`credentials.json`, `token.json`, `transactions.db`) against accidental commit.

Threat model for a single-user, laptop-local app:

- Any website open in the user's browser issuing requests to `localhost:8000`
  (cross-origin reads/mutations, DNS rebinding).
- Other devices on the LAN reaching a `0.0.0.0`-bound server.
- Accidental `git add -f` of live secrets.

## Design

### 1. CORS restriction — `backend/app/main.py`, `backend/app/config.py`

- New setting `CORS_ORIGINS: List[str]` defaulting to
  `["http://localhost:3000", "http://127.0.0.1:3000"]`; used as
  `allow_origins` in the CORS middleware (replacing `["*"]`).
- `allow_credentials=False` — the app uses no cookies; the API key travels in
  a header, unaffected by this flag.
- The `if __name__ == "__main__"` uvicorn call binds `127.0.0.1` instead of
  `0.0.0.0`. The PyCharm run config controls the real bind host; docs note it
  should be `127.0.0.1` as well.

### 2. API-key guard — `config.py`, `api/api_v1/dependencies.py`, `main.py`

- New required setting `API_KEY: str` (no default — startup fails with a clear
  Pydantic validation error if unset, same pattern as `OPENAI_API_KEY`).
- Remove dead `SECRET_KEY` / `ACCESS_TOKEN_EXPIRE_MINUTES` settings (audit Low
  finding "dead auth config"; actively misleading once real auth exists).
- `verify_api_key` dependency in `dependencies.py`:
  - `fastapi.security.APIKeyHeader(name="X-API-Key", auto_error=False)`
  - compare with `secrets.compare_digest`
  - raise `HTTPException(401)` on missing or wrong key.
- Applied at router-include time in `main.py`
  (`app.include_router(..., dependencies=[Depends(verify_api_key)])`) so every
  current and future route on both routers is covered.
- `/docs` and `openapi.json` remain open (metadata only, localhost only).
- A generated random key goes into the local untracked `backend/app/.env`;
  `.env.example` gains an `API_KEY=` line.

### 3. Frontend sends the key — `frontend/src/services/api.js`

- Axios instance: default header `X-API-Key: process.env.REACT_APP_API_KEY`.
- The raw-`fetch` rules functions add the same header.
- Local untracked `frontend/.env` gains `REACT_APP_API_KEY` (same value as the
  backend); new `frontend/.env.example` documents `REACT_APP_API_BASE_URL` and
  `REACT_APP_API_KEY`.

### 4. Pre-commit secret scan

- `brew install gitleaks`.
- Tracked hook script `.githooks/pre-commit` that:
  1. Hard-blocks commits whose staged paths match known sensitive files
     (`.env`, `credentials.json`, `token.json`, `*.db`,
     `classification_rules.json`) — catches `git add -f`.
  2. Runs `gitleaks protect --staged` for content-based detection; if gitleaks
     is not installed, warn loudly but do not block (path-based guard above
     still applies).
- Wired via `git config core.hooksPath .githooks` (local, one-time); the setup
  step is documented in CLAUDE.md so it survives re-clones.

### 5. Testing

- Seed backend test infra: `pytest` + `httpx` as dev dependencies
  (`backend/requirements-dev.txt`), `backend/tests/`.
- `backend/tests/test_auth.py` via FastAPI `TestClient` with settings
  overridden for tests:
  - request without `X-API-Key` → 401
  - request with wrong key → 401
  - request with correct key → passes the guard (any non-401 outcome)
  - CORS: disallowed origin gets no `Access-Control-Allow-Origin`; allowed
    origin does.
- Manual verification: backend + frontend running, app works end-to-end;
  `curl` without the header gets 401; hook blocks a staged `.env`.

## Error handling

- Missing `API_KEY` env → startup failure with Pydantic validation error.
- Missing/stale frontend key → 401 surfaced through the existing axios error
  interceptor.
- gitleaks absent at commit time → warning, path-based blocking still active.
