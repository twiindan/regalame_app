# Local read-only Search Console OAuth export

Provide a small local CLI that securely connects to Google Search Console and exports the last 90 days of final query/page analytics for **`sc-domain:regalame.app`**. This is the only ODD planning artifact. T1 implementation checks and native review passed; T2 real OAuth/export and valid-session reuse succeeded. Work-unit commit and delivery scope remain pending.

## Objective, problem, and why

Manual Search Console downloads interrupt SEO analysis and make repeatable exports harder. Provide a reusable local OAuth session and private export without integrating Google credentials into the production application or changing its dependency baseline.

## Authorized scope and current boundary

- The user approved local read-only OAuth access and confirmed the exact domain property `sc-domain:regalame.app`.
- The user explicitly selected an existing desktop OAuth client in Downloads. Documentation uses `<OAUTH_DESKTOP_CLIENT_JSON>` only; its exact filename and contents must not enter repository artifacts, logs, or memory.
- T2 used that selected client for authorized browser consent and read-only Search Console requests. Do not discover or reuse ambient credentials or other authenticated sessions.
- **T1 is now explicitly authorized:** local implementation, isolated dependency installation into the repository venv, strict mocked TDD, documentation, and verification. The earlier preparation-only boundary described a prior worker scope, not current human authority. No redundant authorization request is needed.
- T2 browser login and live verification are complete following explicit user authorization. The current bounded progress/analytics update reads only the existing export; it must not read credentials or tokens, open a browser, or make new network/API calls.
- The user accepted an independent private copy of the selected client from its read-only source, allowing source hardlinks solely to obtain that copy. The source remains unchanged; the resulting private copy must be mode `0600` and single-link. Token/export storage protections remain unchanged.
- Observed baseline: `main` at `438c97c`; branch `feature/search-console-oauth` was created before the first feature write. Untracked `sample.json` remains unread and untouched. CodeGraph already failed this session; filesystem context was used without retrying.

## Constraints

- Local CLI only: no application routes, production integration, remote execution/deployment, credential transfer, PR creation, push, or automatic commits.
- Keep credentials, tokens, and exports outside the repository. Use owner-only directories (`0700`) and files (`0600`); validate storage destinations and reject repository-local private data before writing.
- Never log secrets, authorization codes, tokens, credential contents, private query rows, or identifying credential filenames. Operational evidence must be sanitized.
- Request only `https://www.googleapis.com/auth/webmasters.readonly`. Google enforces this scope at the account level, **not per property**; the CLI must enforce the exact property itself.
- Keep dependencies in `requirements-search-console.txt`; do not change production `requirements.txt`. Preserve the existing Python 3.13 baseline, requests 2.32.5, and pytest 8.2.2.
- No separate SDD route, proposal, design, plan, or task artifacts. Read existing testing configuration only as the TDD policy source.

## Accepted minimal design

| Area | Decision |
| --- | --- |
| Entry point | Thin `jobs/search_console.py` CLI; no framework, service layer, scheduler, or production wiring. |
| OAuth | Official `google-auth-oauthlib` `InstalledAppFlow` for the selected desktop client. Enable PKCE, retain library state validation, use a loopback-only callback with an ephemeral port (`port=0`), and bound the browser/callback wait. Verify the chosen library version supports these settings. |
| Session | Reuse the private token file; refresh when possible. Revoked/expired refresh credentials or unusable sessions produce a clear reauthorization instruction, not a retry loop or secret-bearing traceback. |
| Property | Hardcode `sc-domain:regalame.app` or reject any supplied value that differs exactly. Never list/query unrelated properties. |
| Transport | Use the official authentication library with the existing requests transport and a small Search Console REST query function; bound HTTP waits and report sanitized failures. |
| Export | Query `searchAnalytics.query` with dimensions `query` and `page`, search type `web`, and `dataState=final`. Use the 90 calendar days ending yesterday in Search Console's reporting timezone; record the requested date range. Paginate using `startRow`/`rowLimit` until exhaustion; keep property, date range, and query settings fixed across pages. |
| Interpretation | Explain that final recent days can be absent due to reporting latency, anonymized queries are omitted for privacy, and Search Analytics returns top rows rather than guaranteed exhaustive data. Pagination does not remove those limits; empty data is not proof of an authentication failure. |
| Output | Write a simple private JSON export with rows and non-secret metadata (property, dates, dimensions, final-data setting, and limitations). Do not print query rows to shared logs. |
| Files | `jobs/search_console.py`, `tests/test_search_console.py`, `requirements-search-console.txt`, `docs/search-console.md`; narrowly scoped `.gitignore` safeguards only if needed, never as a substitute for external private storage. |

## Task checklist and acceptance

### T1 — Implement the CLI, tests, and user documentation as one work unit

- [ ] **T1**: Deliver the minimal local secure OAuth/export behavior with tests, isolated dependencies, and usage/security documentation together.
- [x] Implementation and local fake-boundary checks passed; evidence below.
- [x] Parent-managed native review was explicitly granted, approved, and acknowledged; see latest operational evidence. No commit, push, or PR was performed.
- [ ] Work-unit commit and delivery scope remain pending.

Acceptance:

- Strict red → green → refactor evidence exists for the behavior. Tests use fake OAuth/API boundaries and temporary synthetic files; never actual credentials, browser login, or live Google calls.
- Tests cover exact property and scope enforcement; private external storage and restrictive permissions; PKCE/state/loopback/bounded-wait configuration; token reuse, refresh, and clear reauthorization; sanitized failures and bounded network calls.
- Tests cover the 90-day final-data request, stable query/page pagination, empty results, API failures, and private output metadata. Documentation discloses privacy filtering, top-row limits, and recent-data latency.
- CLI/help and documentation explain the selected-client placeholder, private paths, consent, repeat runs, reauthorization, and dependency installation without exposing credential details.
- Record exact test commands/results, local fake-boundary CLI runtime evidence, authored line count, and rollback boundary. Tests alone do not prove browser consent or real Google access.
- Rollback removes the four feature files and only feature-specific ignore rules; production behavior and unrelated files remain unchanged. Private credentials/exports are not repository rollback artifacts.

### T2 — Perform authorized browser login and real query verification

- [x] **T2**: After T1 passes, use the explicitly selected desktop client for local browser consent, query only `sc-domain:regalame.app`, and create the private export outside the repository.

Acceptance:

- The selected client/session is used without ambient credential discovery. Any change of client, account authorization, property, scope, destination, or remote operation requires renewed explicit authorization.
- Actual browser consent, callback completion, and a real read-only API response are observed. Verify the exact property and requested range/dimensions/final setting; check export location and permissions without publishing its contents.
- Check a repeat run reuses the private session; record refresh/reauthorization evidence only if actually exercised. An empty response may be valid; distinguish it from API/authorization failure.
- Record sanitized command/scenario, outcome, timestamp, and private-export existence/permissions. Do not copy credential values, exact credential filename, tokens, or query rows into evidence. Never fabricate credential, refresh, or live-query proof.
- Operational rollback revokes the grant or deletes the selected local token only with explicit authorization; retain/delete the private export according to the user's direction.

## TDD mode and verification checks

**Mode: strict TDD on.** Verified source: `openspec/config.yaml`, `strict_tdd: true` and `rules.apply.tdd: true`. Runner: `venv/bin/python -m pytest`. Python 3.13, requests 2.32.5, and pytest 8.2.2 remain unchanged. Optional Google dependencies were installed only into the repository venv.

Final foreground checks observed on 2026-10-06, after source/import/layout normalization:

```bash
venv/bin/python -m pytest -q tests/test_search_console.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python -m jobs.search_console --help
```

Results: focused **29 passed in 0.14s**; regression **365 passed in 7.65s**; help **exit 0**. Both pytest runs emitted the existing unset `asyncio_default_fixture_loop_scope` deprecation warning; no unrelated configuration changes were made. `git diff --check` passed. No formatting mutation followed these final checks.

### T1 implementation evidence

Every cycle used `venv/bin/python -m pytest -q tests/test_search_console.py`:

| Cycle | Observed RED | Observed GREEN |
| --- | --- | --- |
| Pacific date window and private atomic storage | 8 failed in 0.04s: CLI absent | 8 passed in 0.02s |
| OAuth configuration, reuse/refresh, and reauthorization | 10 failed, 8 passed in 0.17s: credentials behavior absent | 18 passed in 0.11s |
| API pagination, metadata, errors, and CLI | 8 failed, 19 passed in 0.16s: query/CLI absent | 27 passed in 0.13s |
| Forced OAuth timeout, ambient transport isolation, unsafe ancestors | 4 failed, 25 passed in 0.15s: timeout=None, environment trusted, writable ancestor accepted | 29 passed in 0.13s |
| Refresh redirect and internal-session isolation | 2 failed, 27 passed in 0.15s: isolation options absent | 29 passed in 0.13s |

Refactor evidence: removed the bootstrap module proxy after initial GREEN, extracted the storage-error constant, and normalized imports/control-flow/layout after behavior was GREEN. The final focused and regression checks above remained GREEN.

- Safe mock CLI proof: `venv/bin/python -m pytest -q tests/test_search_console.py::test_cli_fake_boundaries_repeat_run` → **1 passed in 0.08s**. Real CLI parsing, synthetic private JSON writes, two runs, one fake browser-consent boundary, token reuse, exact endpoint, sanitized output, and file permissions were exercised. No browser, actual credentials, or live Google request was used.
- Version resolution: pip metadata/dry-run selected compatible available versions; installed `google-auth 2.60.0`, `google-auth-oauthlib 1.5.0`, `requests-oauthlib 2.0.0`, `oauthlib 4.0.0`, `pyasn1 0.6.4`, and `pyasn1-modules 0.4.2`. Only the four direct Google/OAuth dependencies are pinned in the separate requirements file; production requirements are untouched.
- Runtime library confirmation: inspected installed official flow/transport source and signatures. Version 1.5.0 supports `bind_addr`, `port=0`, `timeout_seconds=180`, and empty `authorization_prompt_message`. Offline tests exercised S256 PKCE and rejection of a mismatched state. Requests-oauthlib passes `timeout=None` during exchange, so a forced request wrapper is required rather than a partial default. OAuth/API/refresh requests use 30-second timeouts; redirects and ambient credential/proxy discovery are disabled. These are network inactivity limits, not a whole-export deadline.
- Changed implementation paths: `jobs/search_console.py`, `tests/test_search_console.py`, `requirements-search-console.txt`, `docs/search-console.md`, and narrow `.gitignore` rules. This task document is also updated; no application or production dependency files changed.
- Rollback boundary: remove the four feature files and the six feature-specific ignore additions; reconcile this task record. Private files/grants are outside repository rollback and require explicit authorization.
- Authored review count: **746** additions plus deletions including this complete previously untracked task document (**122** lines); implementation/guide/requirements/ignore subtotal **624**. This exceeds the advisory 400-line budget and is reported to the parent before any commit; coverage was not removed or compressed.

## Review workload and delivery

| Work unit | Forecast authored additions + deletions |
| --- | ---: |
| This ODD document plus T1 implementation, tests, isolated dependencies, and usage docs | Actual count above; original forecast was approximately 350 |
| T2 sanitized operational evidence update | Small; measure when authored |

The forecast is a planning estimate, not an artificial code-size cap. Include this planning document and later evidence edits in the actual review candidate's authored count. Keep tests and docs with behavior; do not compress or remove coverage to fit a budget.

- **Delivery default: `ask-on-risk`.** The actual scope exceeds 400 authored lines. Parent delivery must decide a coherent slice or explicit exception before commit/delivery. The authorized bounded implementation was not stopped or minimized merely to fit the advisory budget.
- RDD is globally on. Native review completed for the frozen T1 implementation; the later passive progress update is separate. Commit evidence remains **pending**; this checklist is not a receipt or delivery authorization.
- Branch-first requirement was met: `feature/search-console-oauth` from `main` at `438c97c`. T1 is one coherent work-unit candidate, not separate code/test/docs commits. Record its eventual commit identity and previous reviewed boundary here only after commit authorization and applicable gates are satisfied.
- T2 is operational verification, not a fabricated source commit. Record only genuine evidence and any later authorized evidence-document commit.
- No commits are authorized now. No remote deployment, PR creation, or push is authorized by this plan. If delivery later requires a chain, record chosen strategy and exact commit/slice boundaries here after approval.

## Next step

Decide over-budget delivery scope before any commit. T1 implementation and native review passed, but T1 remains unchecked until work-unit delivery is recorded. T2 is complete; refresh and revocation were not exercised. The existing private export can inform a bounded SEO recommendation, not complete-property metrics or guaranteed impact. The safe runtime command template is in `docs/search-console.md`.

## Latest operational evidence

- Parent repeated the focused check: **29 passed in 0.12s**. Native medium-risk reliability review was explicitly granted, approved with non-blocking observations, and acknowledged; authority was burned for the reviewed T1 bytes. This is not commit, push, or PR authorization.
- The initial metadata preflight block (source mode `0644`, two hardlinks) was resolved by the user's accepted independent-copy boundary above. The selected source was treated as read-only and remains unchanged; no token/export storage protections were weakened.
- Parent-observed live verification on 2026-10-06: user test-allowlist access enabled consent; the first run with `--reauthorize` exited **0**, with browser consent, loopback callback, token exchange, and a real read-only API response observed. A repeat run without `--reauthorize` exited **0** and reused the valid private session without new consent. Refresh and revocation were not exercised.
- Verified private storage under `~/.regalame-search-console`: directory mode `0700`; client copy, token, and export are regular single-link files with mode `0600`. No credential contents, identifying filenames, token values, or query rows are recorded here.
- Existing export readback confirms **12 query/page rows**, exact property `sc-domain:regalame.app`, requested dates **2026-07-08 through 2026-10-05**, dimensions `query`/`page`, type `web`, `dataState=final`, and timezone `America/Los_Angeles`. Privacy filtering, top-row limits, and recent-final-data latency remain applicable; these rows are not complete property totals.
- This progress update changes only the existing ODD task record and its full memory mirror. The previously approved and acknowledged native review authority remains burned for unchanged T1 source bytes; this update does not renew authority. No new API call, browser action, source edit, commit, push, PR, or deployment was performed. Delivery decision and work-unit commit remain pending.
