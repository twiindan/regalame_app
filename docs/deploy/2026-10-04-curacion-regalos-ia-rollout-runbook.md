# Rollout runbook — `curacion-regalos-ia` editorial curation

Work Unit 7 / PR 7 of `curacion-regalos-ia`. This is the operator runbook for
turning on AI-assisted gift-catalog curation: environment variables, the two
Railway cron services, the migration gate, the rollout sequence, how to enable
`enforce`, and how to roll back.

Nothing here changes application behavior on its own. The schema migration is
verified by the companion runbook
[`2026-10-04-curacion-regalos-ia-migration-runbook.md`](./2026-10-04-curacion-regalos-ia-migration-runbook.md);
this document integrates that step by reference and does not repeat it.

## Components

| Piece | Path | Role |
|-------|------|------|
| Decision models | `models.py` | `EditorialDecision` (one row per product) + `EditorialGateState` (single gate row) |
| Domain + query logic | `curation.py` | policy constants, fingerprint, effective mode, visibility predicates |
| Provider adapter | `curation_provider.py` | NaN Builders OpenAI-compatible HTTP client (injectable transport) |
| Classification job | `jobs/classify_catalog.py` | incremental, resumable, bounded provider classification |
| Evaluation gate | `jobs/evaluate_curation.py` | offline quality gate over human labels; writes the gate row |
| Web wiring | `catalog.py`, `main.py`, `services.py`, `templates/blog_post.html` | mode-gated filtering of public surfaces |

## Environment variables

All values are read once at **module import** (repo `os.getenv` convention), so
changing any of them requires a **restart or redeploy** of the service that reads
it — for the web service, `EDITORIAL_FILTER_MODE` in particular.

| Variable | Default | Read by | Purpose |
|----------|---------|---------|---------|
| `EDITORIAL_FILTER_MODE` | `off` | `curation.py` | Filter mode. `off` = shadow (public behavior unchanged); `enforce` = apply the editorial predicate **only if the gate passes** (see below). |
| `EDITORIAL_PROVIDER_BASE_URL` | `https://api.nan.builders/v1` | `curation_provider.py` | Provider base URL; the adapter POSTs to `<base>/chat/completions`. |
| `EDITORIAL_PROVIDER_MODEL` | `qwen3.6` | `curation_provider.py` | Model id; also an input to the reclassification fingerprint. |
| `EDITORIAL_PROVIDER_API_KEY` (preferred) / `NAN_API_KEY` | *(none — secret)* | `curation_provider.py` | Bearer token for the provider. Supply it as `EDITORIAL_PROVIDER_API_KEY`; the adapter also accepts the shared `NAN_API_KEY` as a fallback (preferred name wins when both are set). Required for any non-dry-run classification run; the adapter refuses to call out without either. |
| `EDITORIAL_JOB_COMMIT_EVERY` | `25` | `jobs/classify_catalog.py` | Commit the in-flight decisions every N products (the decision table itself is the resumability checkpoint). |
| `EDITORIAL_JOB_RPM` | `60` | `jobs/classify_catalog.py` | Max provider requests per minute; the job spaces sequential requests to respect it. `0` disables the pacing. |
| `EDITORIAL_JOB_MAX_SECONDS` | `3300` | `jobs/classify_catalog.py` | Wall-clock bound per run (55 min, under the ~61 min cron floor). Reaching it stops cleanly and defers the rest. |
| `EDITORIAL_JOB_MAX_PRODUCTS` | `500` | `jobs/classify_catalog.py` | Per-run product cap. `--limit` on the CLI overrides it. |

### Policy constants (NOT environment variables)

Two values are **code constants**, not env vars. Documenting them as env vars
would be wrong — they are not read from the environment:

- `EDITORIAL_POLICY_VERSION` (`curation.py`) — currently `"1"`. Bumping it
  invalidates every AI fingerprint, forcing a full reclassification, and causes a
  stale gate pass to no longer authorize `enforce`. A bump is a code change +
  spec update, deployed with a redeploy.
- `EDITORIAL_CONTEXTS` (`curation.py`) — currently an empty `frozenset`. At v1 a
  `contextual` decision is valid only when its context equals the product's own
  `category_slug`. Widening it to a curated superset is a `EDITORIAL_POLICY_VERSION`
  bump.

## Railway cron services

The curation jobs run out-of-band, exactly like `jobs/refresh_catalog.py`: they
are **separate Railway services** pointing at the same repository, never the web
`Procfile`. Each service needs its own cron entry.

### `python -m jobs.classify_catalog` — classification backfill / shadow

1. Railway → same project → **New Service** → same repository.
2. In **Settings**, before it runs:
   - **Cron Schedule:** e.g. `30 4 * * *` (UTC; minimum 5 minutes between runs).
   - **Restart policy:** `Never`.
   - **Build → Dockerfile path:** `scraper/Dockerfile` (same build as the other job).
   - **Start command:** `python -m jobs.classify_catalog`.
   - **Root directory:** repository root.
3. Environment: `DATABASE_URL` (`${{Postgres.DATABASE_URL}}`),
   `EDITORIAL_PROVIDER_API_KEY` (or the shared `NAN_API_KEY`), and optionally
   `EDITORIAL_PROVIDER_BASE_URL`, `EDITORIAL_PROVIDER_MODEL` and the
   `EDITORIAL_JOB_*` bounds.
4. Useful flags: `--dry-run` (select and report only; zero provider calls, zero
   writes), `--limit N`, `--max-seconds N`.

### `python -m jobs.evaluate_curation` — evaluation gate

1. Same service recipe as above, with **Start command:**
   `python -m jobs.evaluate_curation`.
2. This job is **offline** (zero provider calls). It reads a human-labels JSON
   file and upserts the single `editorial_gate_state` row.
3. Typical use is **not scheduled**: run it once per evaluation cycle.
   - Emit the stratified template (no gate write):
     `python -m jobs.evaluate_curation --sample-out sample.json`.
   - Human-label each entry's `expected_state` (one of the four states).
   - Evaluate and record the verdict:
     `python -m jobs.evaluate_curation --labels sample.json`.
   A malformed or partially-filled labels file exits `1` **without** writing the
   gate row.

### The restart-loop caveat (both jobs)

**Set the Cron Schedule and `Restart policy: Never` before the first run.** A
service deployed without its schedule uses Railway's default `On Failure` policy
with up to 10 retries, so a failure would restart the run repeatedly, re-issuing
provider traffic and re-classifying. The classification job is idempotent and
resumable (committed decisions are skipped), so restarts do not corrupt state —
but the restart loop still burns provider quota and time. The job exits `0` on a
clean stop (including a reached bound) and `1` only on a fatal startup error.

## Migration step

Run the companion Postgres verification **before** deploying this change:
[`2026-10-04-curacion-regalos-ia-migration-runbook.md`](./2026-10-04-curacion-regalos-ia-migration-runbook.md)
(`alembic upgrade head` on a production snapshot, assert the two tables exist and
`product` / `productlist` are unchanged, exercise a read route, `alembic downgrade -1`,
re-`upgrade head`). CI never runs Alembic — `tests/conftest.py` uses
`SQLModel.metadata.create_all` — so this manual step is the only executable proof
the migration applies and reverts cleanly.

## Rollout sequence

1. **Deploy with `EDITORIAL_FILTER_MODE` unset ⇒ `off` (shadow).** The T1/T2
   tests prove zero public change: under `off` the request path performs zero
   editorial DB reads and appends zero SQL, and the off-mode surface snapshots
   match byte-for-byte.
2. **Shadow classification backfill.** Create the classify cron service. First
   run it with `--dry-run` to confirm selection and count, then without it to
   persist decisions (still `off`, zero public effect). Run until **100% of active
   products** hold a decision — coverage reaches `1.0` only when the job selects
   zero pending products. Re-running is safe: a completed backfill makes zero
   calls.
3. **Evaluation gate.** Emit the stratified sample
   (`--sample-out`), human-label it, then run `--labels`. The gate passes only
   when:
   - `overall_agreement >= 0.90`, AND
   - `excluded_leak_ratio <= 0.05` (no human-labeled `excluded` item classified
     `eligible`), AND
   - `coverage_ratio == 1.0`.
   A residual `unknown_ratio > 0.10` passes but is flagged as a SHOULD-threshold
   warning — decide whether to iterate the prompt (policy bump) or accept it.
4. **Enable `enforce`.** Only after the gate row records `gate_passed=true` with
   `coverage_ratio == 1.0` at the current `EDITORIAL_POLICY_VERSION`, set
   `EDITORIAL_FILTER_MODE=enforce` on the **web** service and redeploy. Under
   `enforce`: general surfaces show only `eligible`; `contextual` appears only
   under its matching `/ideas/{slug}` context; `excluded`/`unknown` (and no-row)
   are hidden; categories with zero visible products leave the navigation and the
   sitemap.

## Enabling `enforce` — exact precondition

`curation.effective_filter_mode(session)` returns `enforce` **only when all** of
these hold; otherwise it returns `off`:

- `EDITORIAL_FILTER_MODE == "enforce"`, AND
- the single gate row exists with `gate_passed is True`, AND
- `gate.coverage_ratio == 1.0`, AND
- `gate.policy_version == EDITORIAL_POLICY_VERSION` (a stale gate pass cannot
  authorize a new policy).

A missing, failed, or stale gate row makes `enforce` behave as `off`.

## Rollback

1. **Primary — config flip.** Set `EDITORIAL_FILTER_MODE=off` (or
   `DELETE FROM editorial_gate_state`) and restart/redeploy the web service.
   Public surfaces revert instantly; persisted decisions become inert. **No code
   revert required.**
2. **Job misbehaves** (cost/rate/quality): remove the cron entry. Persisted
   decisions are harmless while `off`.
3. **Bad policy classified:** bump `EDITORIAL_POLICY_VERSION` → all AI
   fingerprints go stale → the next job runs reclassify. Manual overrides keep
   winning.
4. **Schema:** `alembic downgrade -1` is available and verified in the migration
   runbook, but is not required for behavior rollback.

## Verification

- Full suite: `python -m pytest -q --ignore=tests/test_e2e.py`.
- Confirm the documented variable names match the code:
  `grep -rn 'os.getenv("EDITORIAL' curation.py curation_provider.py jobs/classify_catalog.py`.
- Shadow proof: with `EDITORIAL_FILTER_MODE` unset, `tests/test_editorial_filtering.py`
  asserts no executed statement references `editorial_decision` /
  `editorial_gate_state`, and that off-mode responses match `tests/baselines/`.
