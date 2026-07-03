# Design: Fi-Mi-Cash Current State & Roadmap Document

**Date:** 2026-07-02
**Branch:** address-tech-debt
**Status:** Approved

## Goal

Produce a single working-roadmap document that records what the application does
today, every issue found in a full code audit, functional gaps, and a prioritized
list of near-term features. The document is written for the project owner and for
future Claude Code sessions to drive subsequent work.

## Deliverable

One file: `docs/ROADMAP.md`, committed to the `address-tech-debt` branch, with
four sections:

1. **Current State** — what the app does today (feature inventory) and the
   architecture facts needed to reason about changes (lazy Gmail sync with gap
   detection, OpenAI + rules-file classification, SQLite storage, single-fetch
   React frontend). This complements CLAUDE.md; it describes behavior, not
   development setup.
2. **Issues** — findings from a full audit (see method below), grouped by
   severity, each with location and impact.
3. **Gaps** — things the app arguably should already do given its purpose.
4. **Recommended Features** — near-term, personal-use features, prioritized,
   each with a one-line rationale and rough effort (S/M/L).

## Audit method

- Read every backend source file (~25 under `backend/app/`) and every frontend
  source file (~20 under `frontend/src/`) end-to-end. The codebase is small
  enough for an exhaustive read; no sampling.
- Every claimed bug must be verified by reading the complete code path, not by
  pattern-matching on suspicious-looking code.
- Each finding records: severity, location (`file:line`), what is wrong, and
  concrete impact.

### Severity scale

| Severity | Meaning | Known examples going in |
|----------|---------|------------------------|
| Critical | Security or data-loss exposure | Real Gmail `credentials.json`, `token.json`, `.env` (with OpenAI key), and `transactions.db` present in the working tree; CORS `allow_origins=["*"]` with credentials allowed; no authentication on any endpoint |
| High | Produces wrong results or breaks | `average_transaction` in `transaction_service.py:133` sums included (non-excluded) transactions but divides by the count of all transactions |
| Medium | Reliability risk / architectural debt | No backend tests; parser hardcoded to one NCB email format (silent skip on change); hardcoded fallback exchange rate of 159 JMD/USD; CWD-relative runtime paths |
| Low | Cleanup | Dead code, inconsistent patterns (e.g., duplicate classifier singletons in `dependencies.py`, axios + fetch mixed in `api.js`) |

The "Known examples" column is illustrative, not the finding list; the audit
produces the definitive list.

## Gaps vs. Features distinction

- **Gap**: missing capability the app's existing purpose implies — e.g., no way
  to re-classify a single transaction (only merchant-wide rules), no
  month-over-month comparison, no visibility into or manual control over sync.
- **Feature**: net-new value for a single NCB-card user — e.g., budgets, trends,
  CSV export. Big-vision items from the README (multi-bank, mobile app,
  predictions, multi-currency) are explicitly out of scope.

Features are prioritized into an ordered checklist; each entry gets a one-line
"why" and an S/M/L effort estimate grounded in the current architecture.

## Out of scope for this effort

- No code fixes are applied. The document is the sole deliverable. Fixes and
  features become follow-up work items picked off the roadmap in later sessions.
- No changes to README.md or CLAUDE.md beyond what already exists (though the
  audit may note README claims that don't match reality, e.g., alembic
  migrations and lint commands that don't exist).

## Success criteria

- Every backend and frontend source file has been read during the audit.
- Every issue in the doc has a verified `file:line` reference and stated impact.
- The doc is self-contained: a future session can pick any item and start work
  without re-deriving context.
