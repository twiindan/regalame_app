# Search Console full-property baseline (roadmap item 4, WU-A)

ODD planning artifact for this feature. Single feature document (no separate plan file).
Roadmap source: `seo/next-improvements-roadmap` (Engram obs #932), item 4, work unit A.

## Objective, problem, and why

Roadmap item 4 asks for a **measured** Search Console baseline (full property + page/query)
plus privacy-scoped conversion events. This document covers **WU-A: the measured baseline**.

The recovery commit `009a849` landed the local read-only Search Console export CLI (the
former `feature/search-console-oauth` WIP that had been reviewed and approved in a prior
session but never committed). That CLI exports only the `query`+`page` cut. The observed
90-day export is 12 query/page rows, all pointing at the homepage and essentially brand
variants/misspellings, with ~1 click and ~148 impressions total. That is a real but very
thin signal, and it is **not** a full-property baseline: it has no property totals, no
date trend, and no page-only or query-only cuts.

WU-A extends the CLI to emit a combined baseline so SEO decisions rest on measured data
instead of a single narrow cut.

## Authorized scope and current boundary

- Authorized: local implementation in branch `feature/search-console-baseline` (from `main`
  at `e74c6a9`), strict TDD, tests, one work-unit commit per task, and a local read-only run
  against the already-authorized `sc-domain:regalame.app` OAuth session.
- Authorized: the pending work-unit commit of the recovered CLI (`009a849`).
- Not authorized: push, PR, merge, deploy, or any other remote operation; changing the
  Google grant, scope, or property; opening a browser consent flow without renewed approval.
- Private data stays outside the repository under `~/.regalame-search-console/` (`0700` dir,
  `0600` files). No query rows, tokens, or credential filenames enter repository artifacts,
  logs, or memory.
- Out of scope: WU-B (privacy-scoped conversion events, roadmap item 4), production
  integration, schedulers, and any application route change.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `query_baseline(session, now, row_limit)` | runs one fixed query per section and returns a combined report |
| sections | `totals` (`[]`), `byDate` (`["date"]`), `topPages` (`["page"]`), `topQueries` (`["query"]`), `queryPage` (`["query","page"]`), all with the same dates/type/dataState |
| pagination | each section paginates independently with `startRow`/`rowLimit` until a short/empty page |
| metadata | property, startDate, endDate, type, dataState, timezone, limitations, and the section→dimensions map |
| CLI | unchanged arguments; writes the baseline atomically with private permissions |
| failures | sanitized `SafeError`; no secrets or rows; existing export untouched on failure |
| docs | `docs/search-console.md` explains the sections and their privacy/latency limits |

## Constraints

- No new dependencies; keep `requirements-search-console.txt` and the production baseline unchanged.
- Request only `webmasters.readonly`; enforce the exact property `sc-domain:regalame.app`.
- Never log or persist query rows to shared logs; the export stays private and atomic.
- Business logic stays out of `main.py`; this is an isolated `jobs/` CLI with no app imports.

## Files

- `jobs/search_console.py` — replace `query_export` with `query_baseline` + a shared paginating
  `_fetch_section`; add the `SECTIONS` mapping and the section→dimensions metadata.
- `tests/test_search_console.py` — per-section pagination, section ordering/dimensions,
  combined metadata, sanitized failures, and the updated CLI output shape.
- `docs/search-console.md` — interpret the five sections; keep the existing privacy/latency limits.

## Task checklist and acceptance

- [x] **WU-A**: extend the CLI to a combined full-property baseline with tests and updated docs.
      Work-unit commit and TDD evidence recorded below.

Acceptance (Given/When/Then):

- Given a mock session, When `query_baseline` runs, Then it issues exactly one paginated query
  per section in `totals, byDate, topPages, topQueries, queryPage` order with the correct
  dimensions and identical dates/type/dataState.
- Given a section whose page fills `rowLimit`, When more rows exist, Then the section paginates
  with increasing `startRow` until a short/empty page; every section shares the same settings.
- Given a non-200 or malformed response, Then a sanitized `SafeError` is raised and no rows or
  secrets are leaked; the existing private export is left unchanged.
- Given the CLI runs on a mocked session, Then the private output is written atomically with
  `0600` and contains the combined `sections` report and metadata.
- Given the export, Then the date range is the 90 inclusive Pacific days ending yesterday and
  the limitations still disclose top-row/exhaustiveness, anonymized queries, and recent latency.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13, requests 2.32.5, pytest 8.2.2 unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_search_console.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python -m jobs.search_console --help
```

## Progress log

- 2026-10-07: recovered the `feature/search-console-oauth` WIP from `stash@{0}`; focused tests
  re-verified on this base (**29 passed**); committed as `009a849`.
- 2026-10-07: WU-A extension implemented with strict TDD (4 RED→GREEN cycles). Evidence:
  focused `tests/test_search_console.py` **30 passed**; full suite `--ignore=tests/test_e2e.py`
  **472 passed**; `jobs.search_console --help` exit 0; `git diff --check` clean. Extension size
  +88/−34 = 122 authored lines.
- 2026-10-07: authorized live read-only run against `sc-domain:regalame.app` succeeded (exit 0);
  private baseline written to `~/.regalame-search-console/search-console-baseline.json` (0600).
  Range **2026-07-09 → 2026-10-06** (90 Pacific days ending yesterday).

### Measured baseline (aggregate only; no raw rows persisted)

- Property totals (90 days): **7 clicks, 290 impressions, CTR 2.4%, average position 12.8**.
- `byDate`: data on 88 days.
- `topPages`: 6 pages — the homepage carries ~283 impressions / 7 clicks; two blog posts and
  three public profiles (`/p/…`) get 1–6 impressions each at positions ~5–10 with **zero clicks**.
- `topQueries`: essentially all brand variants/misspellings of the brand; one non-brand query
  drove the single non-homepage click.
- **Why WU-A mattered:** the old `query`+`page`-only cut showed 12 rows / 1 click and would have
  understated the property (7 clicks). The `page` cut reveals pages whose queries are omitted as
  anonymized for privacy, so query+page alone is provably incomplete. This is the measured
  evidence the roadmap asked for, and it is not complete-property totals on its own.

## Review workload and delivery

- Delivery default: `ask-on-risk` (global RDD is on). The recovered CLI alone is 757 authored
  lines and the extension adds more, so the accumulated branch exceeds the advisory 400-line
  budget. Delivered PR/commit scope is user-owned; this document records the actual counts.
- The recovered CLI bytes were native-reviewed and approved in a prior session; the commit
  boundary is `009a849`. The WU-A extension is a new candidate.
