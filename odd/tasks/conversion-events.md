# Privacy-scoped conversion events (roadmap item 4, WU-B)

ODD planning artifact for this feature. Single feature document (no separate plan file).
Roadmap source: `seo/next-improvements-roadmap` (Engram obs #932), item 4, work unit B.

## Objective, problem, and why

Roadmap item 4 asks for a **measured** Search Console baseline plus **conversion events with
privacy scope**. WU-A (merged, PR #60) delivered the Search Console baseline. There is today
**no analytics provider** and **no on-site conversion measurement**, so the product cannot see
whether visitors become signups, groups, wishes, or draws.

Rather than adding a third-party analytics product (cookies + EU consent banner, data leaving
the app), WU-B records conversions **first-party**, in the app's own database, with a privacy
scope enforced by design: event name + UTC timestamp only, never identifying data.

## Authorized scope and current boundary

- Authorized: local implementation in branch `feature/conversion-events` (from `main`
  `9a9d83a`), strict TDD, tests, Alembic migration, one work-unit commit per task.
- Authorized: a private, read-only local report over the events.
- Not authorized: any third-party analytics/provider integration, client-side scripts, cookies,
  a public reporting route, push, PR, merge, or deploy without explicit approval.
- Privacy is a hard constraint, not a default: see the privacy scope below.

## Privacy scope (hard rules)

- Stored per event **only**: `name` (allowlist) and `occurred_at` (naive UTC, matching the
  module's datetime convention). No properties in v1.
- **Never** stored: user id, email, name, group id/code, wish title/url/content, IP address,
  user-agent, referrer, or any free text.
- No cookies, no client script, no third-party network calls, no public endpoint exposing rows.
- `record_conversion` is a **resilient side-channel**: recording must never break or fail a user
  action. It validates the name against the allowlist and swallows/logs storage errors.
- A documented, versioned allowlist; adding an event is an explicit change to the allowlist.

## Design

| Area | Decision |
| --- | --- |
| Model | `ConversionEvent` in `models.py`: `id`, `name` (indexed), `occurred_at` (naive UTC, `utcnow_naive`, indexed); composite index `(name, occurred_at)`. |
| Service | `services.py`: `CONVERSION_EVENTS` frozenset allowlist and `record_conversion(session, name)` (ignores unknown names; never raises). |
| Allowlist | `signup`, `login`, `group_created`, `invitation_accepted`, `invitation_sent`, `wish_added`, `wish_reserved`, `draw_performed`. |
| Wiring | Called from `main.py` thin routes **after** the action commits successfully (see table). |
| Reader | `jobs/conversion_report.py`: private read-only CLI printing counts per event and per day for the last N days (default 30). No public route. |
| Migration | New Alembic revision `down_revision="b3d9f1a7c250"`; creates `conversion_event` + indexes. Additive, reversible. |
| Docs | `docs/conversion-events.md`: what is collected, the privacy scope, the allowlist, and how to read the report. |

Wiring (event → route, after success):

| Event | Route | Point |
| --- | --- | --- |
| `signup` | `POST /register` | after user commit/refresh |
| `login` | `POST /login` | after session set |
| `group_created` | `POST /create-group` | after member commit |
| `invitation_accepted` | `POST /join/{code}` | after member commit (new member only) |
| `invitation_sent` | `POST /group/{id}/invite` | after queuing, only when the email list is non-empty |
| `draw_performed` | `POST /group/{id}/draw` | after `perform_draw` succeeds |
| `wish_added` | `POST /wishes` | after wish commit/refresh |
| `wish_reserved` | `POST /wishes/{id}/toggle-reserve` | only when the reserve is set (not on un-reserve) |

## Constraints

- Business logic stays in `services.py`; routes stay thin; no business logic in templates.
- No new dependencies; Jinja2 + HTMX + TailwindCSS only; no Node/bundler.
- Keep the pinned dependency baseline and the naive-UTC datetime convention.
- The migration is additive and reversible; no production data is touched.

## Files

- `models.py` — new `ConversionEvent` table.
- `services.py` — `CONVERSION_EVENTS`, `record_conversion`, and a read-only counts helper.
- `main.py` — import `record_conversion`; wire the eight points.
- `alembic/versions/<new>_add_conversion_event.py` — additive migration.
- `jobs/conversion_report.py` — private read-only report CLI.
- `docs/conversion-events.md` — privacy scope + usage.
- `tests/test_conversion_events.py` — model, service, wiring, resilience, report.

## Task checklist and acceptance

- [ ] **T1 — collect**: model + service + migration + the eight route wirings, with tests.
- [ ] **T2 — read**: private report CLI + docs, with tests.

Acceptance (Given/When/Then):

- Given a successful `POST /register`, When the request completes, Then exactly one `signup`
  row exists and no identifying data is stored in it.
- Given each wired route, When the action succeeds, Then exactly one row of the matching event
  is recorded; When the action fails or is a no-op (already a member, un-reserve, empty invite
  list), Then no row is recorded.
- Given an unknown event name, When `record_conversion` is called, Then nothing is stored.
- Given a storage failure inside `record_conversion`, When a wired route runs, Then the user
  action still succeeds and no exception escapes.
- Given the events table, When the report runs for N days, Then it prints per-event and per-day
  counts, read-only, and never exposes rows outside the aggregate.
- Given a fresh database, When the migration runs, Then `conversion_event` and its indexes
  exist; `downgrade` removes them.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_conversion_events.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python -m jobs.conversion_report --help
```

## Progress log

- 2026-10-08: read-only exploration (Engram #1002); branch `feature/conversion-events` created
  from `main` `9a9d83a`; Alembic head confirmed `b3d9f1a7c250`. Implementation pending.

## Review workload and delivery

- Delivery default: `ask-on-risk` (global RDD is on). Forecast is roughly 400 authored lines
  across T1+T2; confirm the actual count at each work-unit commit and decide single PR vs
  `size:exception` before delivery. Delivery is user-owned.
