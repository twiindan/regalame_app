# Conversion events (first-party, privacy-scoped)

Regálame measures its own conversions **first-party**, in the application's own
database. There is no analytics provider, no client-side script, no cookie, and
no third-party network call involved.

## What is collected

Each event row stores exactly two values:

- `name` — one string from the allowlist below.
- `occurred_at` — a naive UTC timestamp (the module's datetime convention).

Nothing else. **Never stored**: user id, email, name, group id or code, wish
title/url/content, IP address, user-agent, referrer, or any free text. The
schema enforces this: the `conversion_event` table has no other columns.

## Event allowlist

The allowlist is the whole vocabulary that may be persisted. Adding an event is
a deliberate change to `CONVERSION_EVENTS` in `services.py`.

| Event | Recorded when |
| --- | --- |
| `signup` | `POST /register` succeeds |
| `login` | `POST /login` succeeds |
| `group_created` | `POST /create-group` succeeds |
| `invitation_accepted` | a **new** member joins via `POST /join/{code}` |
| `invitation_sent` | `POST /group/{id}/invite` queues a non-empty email list |
| `wish_added` | `POST /wishes` succeeds |
| `wish_reserved` | a wish is reserved (not on un-reserve) |
| `draw_performed` | `POST /group/{id}/draw` succeeds |

## Privacy scope (hard rules)

- Event name + UTC timestamp only; no properties in v1.
- No cookies, no client script, no third-party calls, no public route exposing rows.
- `record_conversion` is a resilient side-channel: it ignores unknown names and
  swallows storage errors (logging a warning and rolling back), so recording can
  never break or fail the user action that triggered it.
- The read path returns aggregates only, never row-level data.

## Running the report

The report is a private, read-only local CLI. It opens a session through the
application's own engine and prints per-event totals and per-day counts for a
window, using only aggregate queries.

```bash
venv/bin/python -m jobs.conversion_report --days 30
```

- `--days N` sets the window in days (default `30`; `0` means all recorded time).
- `--help` works without touching the database.
- It performs no writes and prints nothing beyond aggregates.

## Rollback

Remove the CLI, its tests, this guide, the `ConversionEvent` model, the
`record_conversion` calls in `main.py`, and downgrade the Alembic revision
`c4e8a2b6d910`. The migration is additive and reversible.
