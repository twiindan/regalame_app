# Apply Progress: `curacion-regalos-ia`

Merged cumulative progress across all apply batches. Strict TDD mode active.

## Batch: Work Unit 1 / PR 1 — Phase 1: Schema Foundation

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 1 targets `main`; later slices stacked)
**Status:** Complete — 6/6 Phase 1 tasks.

### Completed Tasks

- [x] 1.1 Bootstrap verification environment and record baseline — 128 tests collected (main-repo venv, Python 3.13.5).
- [x] 1.2 RED — model semantics tests in `tests/test_curation.py` (confirmed `ImportError`).
- [x] 1.3 GREEN — `EditorialDecision` + `EditorialGateState` added to `models.py`.
- [x] 1.4 RED/GREEN — additive migration `b3d9f1a7c250` with `down_revision="9f1c7b2a4d3e"` + additive-guard AST test.
- [x] 1.5 Runbook step — manual Postgres verification recorded at `docs/deploy/2026-10-04-curacion-regalos-ia-migration-runbook.md` (CI never runs Alembic).
- [x] 1.6 Verify — `tests/test_curation.py` green; full suite 140 passed.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `models.py` | Modified | Added `EditorialDecision` (`__tablename__="editorial_decision"`, unique indexed FK `product_id`, nullable AI + manual column groups) and `EditorialGateState` (`__tablename__="editorial_gate_state"`, single-row gate fields), after `ProductList`. `Product`/`ProductList` untouched. |
| `alembic/versions/b3d9f1a7c250_add_editorial_decision.py` | Created | Strictly additive migration: `down_revision="9f1c7b2a4d3e"`, `upgrade()` = 2× `create_table` + 1 unique index; `downgrade()` drops in reverse. |
| `tests/test_curation.py` | Created | 12 tests: model semantics (names, unique indexed FK, nullability, naive-UTC timestamp defaults, duplicate `product_id` ⇒ `IntegrityError`) + migration chain/additive guard/downgrade. |
| `docs/deploy/2026-10-04-curacion-regalos-ia-migration-runbook.md` | Created | Manual Postgres upgrade/downgrade verification runbook (PR 1 pre-deploy gate). |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 1 tasks 1.1–1.6 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.2–1.3 | `tests/test_curation.py` | Unit | ✅ 128/128 baseline | ✅ ImportError confirmed | ✅ 8 passed | ✅ 8 cases (2 names, FK+unique, 2 nullability groups, gate cols, timestamps+null manual, duplicate FK) | ➖ None needed (declarative models) |
| 1.4 | `tests/test_curation.py` | Unit | ✅ 128/128 baseline | ✅ migration file absent (4 failed) | ✅ 12 passed | ✅ 4 cases (chain, additivity, created tables, dropped tables) | ✅ helper filtered to `op.*` calls only |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `python -m pytest -q tests/test_curation.py` → **12 passed in 0.05s** |
| Runtime harness command/scenario and exact result | `alembic heads` → **`b3d9f1a7c250 (head)`** (single head, chained to `9f1c7b2a4d3e`). Postgres upgrade/downgrade execution is the CI-external deploy gate recorded in the runbook; not executable in this worktree (no Postgres, CI uses `create_all`). |
| Rollback boundary | Revert `models.py`, delete `alembic/versions/b3d9f1a7c250_add_editorial_decision.py`, `docs/deploy/2026-10-04-curacion-regalos-ia-migration-runbook.md`, and `tests/test_curation.py`. Tables are unused by any consumer; zero behavior change. |

### Deviations from Design

- None semantically. The design's `effective_filter_mode` snippet (Decision 3) omits the `coverage_ratio == 1.0` clause, but that clause is a Phase 2 concern (task 2.6), not part of Work Unit 1.
- `manual_updated_at` intentionally has **no** `default_factory` (stays `None` until an operator sets a manual override). Giving it a default would make `apply_decision` implicitly "write" a manual column, violating the Phase 2 "apply writes AI columns only" contract.
- Test names include the `model` token so the tasks-specified selector `-k model` actually selects the model-semantics suite (migration tests carry the `migration` token).

### Issues Found

None.

### Commits

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `a472668` | `feat(curation): add editorial decision and gate-state models with additive migration` | `models.py`, migration, `tests/test_curation.py` | 339 |
| `522d5b2` | `docs(curation): add manual Postgres migration verification runbook` | `docs/deploy/…migration-runbook.md` | 84 |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main)
- Current work unit: Work Unit 1 — Phase 1 Schema Foundation
- Boundary: starts at verified migration head `9f1c7b2a4d3e`; ends with the two editorial tables + models + tests + runbook. No consumer wired.
- Review budget: **code work unit = 339 authored lines (< 400)** in commit `a472668`. The runbook is an 84-line docs-only commit `522d5b2`; tasks.md also assigns the deployment runbook to Phase 7 (task 7.2) and task 1.5 permits "deploy PR notes", so it may ride the docs PR or be pasted into the PR 1 body.

---

## Batch: Work Unit 2 / PR 2 — Phase 2: Curation Domain Service (`curation.py`)

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 2 targets the PR 1 slice)
**Status:** Complete — 10/10 Phase 2 tasks. Ready for next batch (Work Unit 3 / PR 3).

**Re-slice note (review budget):** the original single Phase 2 commit was 733
authored lines, over the 400-line budget, so it was rewritten into two stacked
work units: **PR 2a** (constants + fingerprint + `pending_products` /
`apply_decision` / `effective_state`) and **PR 2b** (`effective_filter_mode` +
visibility predicates + `visible_category_slugs`). The importer-neutral tests
(`import_from_json` leaves `editorial_decision` untouched, plus the new
"manual override survives import and re-runs" regression test) ship in 2b so
both slices stay under budget — they exercise `catalog.py` interop rather than
`curation.py` internals.

### Completed Tasks

- [x] 2.1 RED — fingerprint rules (`python -m pytest -q tests/test_curation.py -k fingerprint` → `ModuleNotFoundError: No module named 'curation'`).
- [x] 2.2 GREEN — constants + `compute_fingerprint` (JSON-canonical SHA-256) in `curation.py`.
- [x] 2.3 RED — pending selection, apply/upsert, manual-wins, unknown semantics, importer-neutral.
- [x] 2.4 GREEN — `pending_products`, `apply_decision` (AI columns only), `effective_state`, `EDITORIAL_CONTEXTS` v1.
- [x] 2.5 RED — effective mode + enforce preconditions (incl. zero-DB-read off path and `coverage_ratio < 1.0`).
- [x] 2.6 GREEN — `effective_filter_mode` with explicit `gate_passed is True AND coverage_ratio == 1.0 AND policy_version == EDITORIAL_POLICY_VERSION`.
- [x] 2.7 RED — visibility predicates (`general`, `context_category`, None when off).
- [x] 2.8 GREEN — `_EditorialVisibility` + `editorial_visibility`.
- [x] 2.9 RED/GREEN — `visible_category_slugs` (eligible UNION effective contexts; active-only; suppression).
- [x] 2.10 REFACTOR + verify — extracted `_eligible_product_ids` / `_contextual_product_ids`; all green.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `curation.py` | Created | Policy constants (`EDITORIAL_STATES`, `EDITORIAL_POLICY_VERSION`, `EDITORIAL_FILTER_MODE` from env, v1 `EDITORIAL_CONTEXTS`), `compute_fingerprint`, `effective_filter_mode`, `effective_state` + coalesce column helpers, `pending_products`, `apply_decision`, `_EditorialVisibility` + `editorial_visibility`, `visible_category_slugs`, and a structural `DecisionResult` protocol. |
| `tests/test_curation.py` | Modified | +37 Phase 2 tests (fingerprint rules, pending/apply/manual/unknown/importer, effective-mode preconditions, visibility predicates, category slugs) on top of the 12 Phase 1 tests, including the new "manual override survives import and re-runs" regression test. |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 2 tasks 2.1–2.10 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 2.1–2.2 | `tests/test_curation.py` | Unit | ✅ 12/12 Phase 1 | ✅ `ModuleNotFoundError: curation` | ✅ 8 passed (`-k fingerprint`) | ✅ 8 cases (determinism, golden SHA-256, JSON-alias, exact params, 4× input sensitivity, constants) | ✅ extracted subquery helpers |
| 2.3–2.4 | `tests/test_curation.py` | Unit | ✅ 12/12 | ✅ 10 failed (`AttributeError`) | ✅ 11 passed | ✅ 11 cases (active-only, current/stale fingerprint, manual-excluded, limit, upsert no-dup, context normalization both ways, manual untouched, unknown resolution, importer-neutral) | ✅ `_expected_fingerprint` helper |
| 2.5–2.6 | `tests/test_curation.py` | Unit | ✅ 12/12 | ✅ 6 failed | ✅ 8 passed (`-k "effective or enforce"`) | ✅ 6 cases (off zero-read, default, no gate, failed gate, incomplete backfill, stale policy, all-pass) | ✅ |
| 2.7–2.8 | `tests/test_curation.py` | Unit | ✅ 12/12 | ✅ 5 failed | ✅ 7 passed | ✅ 7 cases (None when off, None without gate, general eligible-only, context merge both slugs, cross-category context, hidden set, manual override wins in both branches) | ✅ coalesce subquery helpers |
| 2.9 | `tests/test_curation.py` | Unit | ✅ 12/12 | ✅ 3 failed (`AttributeError`) | ✅ 3 passed | ✅ 3 cases (None when off, eligible+context UNION with differing context, zero-visible suppression + inactive exclusion) | ✅ |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | PR 2a `python -m pytest -q tests/test_curation.py` → **31 passed**; PR 2b → **49 passed** (12 Phase 1 + 37 Phase 2) |
| Runtime harness command/scenario and exact result | **N/A — pure functions + SQL predicate builders, no runtime/I-O boundary.** `curation.py` performs no network or filesystem I/O; its only DB access is the single gate SELECT on the `enforce` path, exercised by the in-memory SQLite session in the focused tests (including a `_NoReadSession` spy proving the `off` path performs zero reads). No consumer imports `curation.py` until PR 6. |
| Rollback boundary | Delete `curation.py` and revert the Phase 2 additions to `tests/test_curation.py`. Nothing imports `curation.py`; zero behavior change. |

### TDD Cycle Summary

- **Total Phase 2 tests written**: 37 (49 in the file total).
- **Total tests passing**: 49/49 focused; 177/177 full suite.
- **Layers used**: Unit (37).
- **Approval tests (refactoring)**: None — no refactoring of existing behavior (new module).
- **Pure functions created**: `compute_fingerprint`, `effective_state`, `_expected_fingerprint`, `_eligible_product_ids`, `_contextual_product_ids` (+ predicate builders).

### Deviations from Design

- `apply_decision`'s `result` parameter is typed with a local structural `DecisionResult` protocol rather than importing `curation_provider.ClassificationResult`. Phase 2 must be independently green and `curation_provider.py` does not exist until PR 3; `curation_provider.ClassificationResult` satisfies the protocol structurally, so no runtime coupling is introduced.
- `EDITORIAL_CONTEXTS` is defined as an (empty) `frozenset` documenting the curated superset. v1's "context equals the product's own `category_slug`" rule is enforced in `curation_provider.parse_provider_response` (PR 3), which receives the allowed slug from the product item — matching task 2.4 and the product-sign-off note.
- The design's Decision 8 `context_category` snippet references the contextual branch without a product correlation; implemented as a `Product.id.in_(<contextual subquery>)` so the predicate correlates to each product (a bare `coalesce(...) == slug` in a `Product` select would cross-join `editorial_decision`).
- `visible_category_slugs` is executed via `session.execute(union).scalars()` because SQLModel's `session.exec` does not scalarize a compound `UNION` select (it returns 1-tuples); behavior matches the design SQL, only the invocation differs.

### Issues Found

None. All 128 baseline tests remain green with no semantic modification (full suite: 177 passed).

### Commits (2a / 2b re-slice)

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `ae30a59` | `feat(curation): add fingerprint and editorial decision persistence` | `curation.py`, `tests/test_curation.py` | 386 (< 400) |
| `7e824d0` | `feat(curation): add effective-mode and visibility predicates` | `curation.py`, `tests/test_curation.py` | 399 (< 400) |
| this artifacts commit | `docs(sdd): track curacion-regalos-ia openspec artifacts` | `openspec/**`, `.gitignore` | artifacts |

The original single commit `bbc5d15` (733 authored lines, over budget) was
replaced by the two commits above. The artifacts-commit hash previously
recorded here (`68d1083`) was stale/wrong and has been removed.

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main); **PR 2 split into PR 2a + PR 2b** to fit the 400-line review budget.
- Work unit 2a: constants + `compute_fingerprint` + `pending_products` / `apply_decision` / `effective_state` / `DecisionResult` — **386 authored lines (< 400)**.
- Work unit 2b: `effective_filter_mode` + `_EditorialVisibility` / `editorial_visibility` + `visible_category_slugs` (+ importer-neutral tests) — **399 authored lines (< 400)**.
- Boundary: starts after the Phase 1 models/migration; ends with the standalone `curation.py` domain module + its 37 tests. No consumer wired (`main.py`/`catalog.py` untouched until PR 6).
- Review budget: every slice is under 400 authored lines and each was verified green independently (`python -m pytest -q tests/test_curation.py`).

### Status

10/10 Phase 2 tasks complete across PR 2a (`ae30a59`, 386 lines) and PR 2b (`7e824d0`, 399 lines). Ready for next batch (Work Unit 3 / PR 3 — `curation_provider.py`).

---

## Batch: Work Unit 3 / PR 3 — Phase 3: Provider Adapter (`curation_provider.py`)

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 3 targets the PR 2 slice)
**Status:** Complete — 3/3 Phase 3 tasks. Ready for next batch (Work Unit 4 / PR 4).

**Re-slice note (review budget):** Work Unit 3 landed as **three** stacked
commits, each a cohesive behavior under the 400-line budget: **3a** pure response
validation, **3b** the production transport + minimal payload, and **3c**
`classify_product` orchestration with bounded retries and the v1 context rule.
The first attempt at a two-way split left the `classify_product` slice at 413
authored lines, so it was split once more rather than exceed the budget. No
tests or code were removed to fit the budget.

### Completed Tasks

- [x] 3.1 RED — `tests/test_curation_provider.py`: invalid-shape ⇒ `None`, transport seam, payload minimization, overrides/env reach the request (`ModuleNotFoundError: No module named 'curation_provider'`).
- [x] 3.2 GREEN — `curation_provider.py` with frozen `ClassificationResult`, `Transport`, strict `DECISION_JSON_SCHEMA`, `POLICY_PROMPT`, `parse_provider_response`, `_post_chat_completions`, and the EXPANDED `classify_product`.
- [x] 3.3 Verify zero-network — injected fake transport everywhere; `requests.post` monkeypatched to a fake (or to a failing sentinel) on the production path.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `curation_provider.py` | Created | Env config (`EDITORIAL_PROVIDER_BASE_URL` / `_MODEL` / `_API_KEY`), `Transport = Callable[[dict], dict]`, frozen `ClassificationResult`, strict `DECISION_JSON_SCHEMA`, `POLICY_PROMPT`, pure `parse_provider_response`, `_post_chat_completions` over `requests`, `_build_payload`, `_allowed_contexts`, and the EXPANDED `classify_product`. |
| `tests/test_curation_provider.py` | Created | 53 tests: validation (well-formed, missing/empty choices, non-object content, enum, contextual context, empty reason, stray-context normalization, schema/prompt/frozen constants), transport/payload (`_post_chat_completions` bearer/url/timeout, env defaults, minimal payload), and `classify_product` (expanded signature, injected transport, bounded retries, timeout/invalid/never-raises, v1 context rule, env/override propagation, zero-network guard). |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 3 tasks 3.1–3.3 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 3.1–3.2 (3a) | `tests/test_curation_provider.py` | Unit | ✅ 177/177 full suite | ✅ `ModuleNotFoundError: curation_provider` | ✅ 31 passed | ✅ 31 cases (valid bodies, 4 missing-choice shapes, 6 non-object contents, 4 enum shapes, 3 contextual-context shapes, 3 reason shapes, stray context, schema/prompt/frozen) | ✅ `_resolve_allowed_contexts` extracted |
| 3.2 (3b) | `tests/test_curation_provider.py` | Unit | ✅ 31/31 provider | ✅ transport/payload names absent (ImportError before implementation) | ✅ 37 passed | ✅ 6 cases (transport contract, env defaults, bearer/url/timeout, no-key refusal, minimal payload, response_format) | ➖ None needed |
| 3.2–3.3 (3c) | `tests/test_curation_provider.py` | Unit | ✅ 37/37 provider | ✅ `cannot import name 'classify_product'` | ✅ 53 passed | ✅ 16 cases (expanded signature, injected transport, minimal build-payload equality, transport error, timeout, 2/3 bounded retries, invalid response, never raises, v1 context rule both ways, no-slug rejection, env/override model, overrides/env reach request, injected transport bypasses `requests.post`, unconfigured key) | ➖ None needed |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | 3a `python -m pytest -q tests/test_curation_provider.py` → **31 passed**; 3b → **37 passed**; 3c → **53 passed** |
| Runtime harness command/scenario and exact result | **N/A in CI — zero network by contract.** The adapter's only runtime boundary is the provider HTTP call; every test injects a fake transport, and the production-transport tests monkeypatch `curation_provider.requests.post` with a fake (or a sentinel that raises if reached). The gated manual harness (one real `classify_product` call with `EDITORIAL_PROVIDER_API_KEY` set) from the tasks/design is intentionally CI-external and was not run in this worktree. |
| Rollback boundary | Delete `curation_provider.py` and `tests/test_curation_provider.py`. Nothing imports `curation_provider` in production yet (`jobs/classify_catalog.py` in PR 4 is the first consumer); zero behavior change. |

### TDD Cycle Summary

- **Total Phase 3 tests written**: 53.
- **Total tests passing**: 53/53 focused; 230/230 full suite.
- **Layers used**: Unit (53).
- **Approval tests (refactoring)**: None — new module.
- **Pure functions created**: `parse_provider_response`, `_resolve_allowed_contexts`, `_build_payload`, `_allowed_contexts`.

### Deviations from Design

- `parse_provider_response` gains a keyword-only `allowed_contexts: Iterable[str] | None = None` (design signature was `parse_provider_response(body)`). The v1 rule needs the product's own `category_slug`, which a pure function of `body` cannot know; `classify_product` supplies `{category_slug} | EDITORIAL_CONTEXTS`. When omitted it defaults to `EDITORIAL_CONTEXTS` (empty at v1), so a contextual body with no product slug is strictly rejected. The positional `parse_provider_response(body)` call form is preserved.
- `_post_chat_completions` gains keyword-only `base_url` / `api_key` / `timeout` so per-call overrides and env-derived values reach the request; `classify_product` binds them with `functools.partial` so the seam stays `Transport = Callable[[dict], dict]` (design Decision 6).
- `classify_product` retries on **both** transport exceptions and invalid responses, bounded by `max_attempts` (total attempts, default 2), then returns `None`. Both are failures the spec says must never be cached, so retrying the invalid case is consistent with "retries are bounded".
- The state enum and the closed context vocabulary are imported from `curation` (`EDITORIAL_STATES` / `EDITORIAL_CONTEXTS`) so the adapter and the domain cannot drift; `curation` never imports `curation_provider`, so there is no cycle.

### Issues Found

None. All 177 baseline tests remain green with no semantic modification (full suite: 230 passed).

### Commits (3a / 3b / 3c re-slice)

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `40f20b1` | `feat(curation): validate provider editorial responses strictly` | `curation_provider.py`, `tests/test_curation_provider.py` | 305 (< 400) |
| `c410f67` | `feat(curation): add provider transport and minimal request payload` | `curation_provider.py`, `tests/test_curation_provider.py` | 190 (< 400) |
| `17d77f9` | `feat(curation): classify products with bounded retries and v1 context rule` | `curation_provider.py`, `tests/test_curation_provider.py` | 256 (< 400) |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main); **PR 3 split into PR 3a + PR 3b + PR 3c** to fit the 400-line review budget.
- Work unit 3a: pure validation (`ClassificationResult`, `DECISION_JSON_SCHEMA`, `POLICY_PROMPT`, `parse_provider_response`) — **305 authored lines**.
- Work unit 3b: env config + `Transport` + `_post_chat_completions` + `_build_payload` — **190 authored lines**.
- Work unit 3c: `_allowed_contexts` + EXPANDED `classify_product` — **256 authored lines**.
- Boundary: starts after the Phase 2 `curation.py` domain; ends with the standalone `curation_provider.py` adapter + its 53 tests. No production consumer yet (Phase 4 job).
- Review budget: every slice is under 400 authored lines and each was verified green independently (`python -m pytest -q tests/test_curation_provider.py`).

### Status

3/3 Phase 3 tasks complete across PR 3a (`40f20b1`, 305), PR 3b (`c410f67`, 190) and PR 3c (`17d77f9`, 256). Ready for next batch (Work Unit 4 / PR 4 — `jobs/classify_catalog.py`).

---

## Batch: Work Unit 4 / PR 4 — Phase 4: Classification Job (`jobs/classify_catalog.py`)

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 4 targets the PR 3 slice)
**Status:** Complete — 8/8 Phase 4 tasks. Ready for next batch (Work Unit 5 / PR 5).

**Re-slice note (review budget):** Work Unit 4 landed as **three** stacked
commits, each a cohesive behavior under the 400-line budget: **4a** the
incremental job core with failure-not-cached decisions, **4b** batched commits
with a resumable run limit, and **4c** the configured rate/wall/product bounds.
No tests or code were removed to fit the budget.

### Completed Tasks

- [x] 4.1 RED — `tests/test_classify_catalog.py`: incremental selection (only pending/stale sent), active-only scope, dry-run zero calls/zero writes.
- [x] 4.2 GREEN — `jobs/classify_catalog.py`: selection via `curation.pending_products`, dry-run early return, valid-only decision persistence.
- [x] 4.3 RED — idempotent re-run (zero calls, no row changes) + resumable run (`limit` reached then restarted).
- [x] 4.4 GREEN — commit every `EDITORIAL_JOB_COMMIT_EVERY` (default 25) via `curation.apply_decision`; the decision table is the only checkpoint.
- [x] 4.5 RED — bounded rate/wall-time/per-run cap + failure-not-cached + job continues after a failed product.
- [x] 4.6 GREEN — sequential loop (concurrency 1), inter-request `_sleep` targeting `EDITORIAL_JOB_RPM`, wall check before each request, per-run cap, `stopped=reason` log.
- [x] 4.7 Runtime harness (manual) — dry-run CLI verified offline (below); the shadow run is CI-external (needs a real `EDITORIAL_PROVIDER_API_KEY`).
- [x] 4.8 Verify — focused suite green; full suite green; no regression.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `jobs/classify_catalog.py` | Created | Job mirroring `refresh_catalog`: module docstring, `_now`/`_sleep` clock seams, `_product_item`, `run(session, classify_fn=curation_provider.classify_product, *, dry_run, limit, max_seconds, log)`, `_log_progress`, `_parse_args`, `main`. Env bounds `EDITORIAL_JOB_COMMIT_EVERY`/`_RPM`/`_MAX_SECONDS`/`_MAX_PRODUCTS`. FIRST production consumer of `curation.pending_products` + `curation_provider.classify_product`. |
| `tests/test_classify_catalog.py` | Created | 21 integration tests: incremental/active-only/dry-run, item contains `category_slug`, valid persistence (eligible/contextual), failure-not-cached (transport failure, invalid response, transient failure retains prior), idempotent re-run, resumable `limit`, batch progress log, env bound defaults, virtual-clock rate/wall/cap bounds, continues-after-failure, CLI parse + injected-session `main`. |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 4 tasks 4.1–4.8 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 4.1–4.2 (4a) | `tests/test_classify_catalog.py` | Integration | ✅ 230/230 full suite | ✅ `ModuleNotFoundError: jobs.classify_catalog` | ✅ 11 passed | ✅ 11 cases (current vs stale vs fresh, active-only, dry-run zero, item slug, eligible/contextual persist, transport failure, invalid response, transient-failure retention, CLI) | ✅ `_product_item` extracted |
| 4.3–4.4 (4b) | `tests/test_classify_catalog.py` | Integration | ✅ 11/11 focused | ✅ `limit` ignored (3 calls, expected 2); `EDITORIAL_JOB_COMMIT_EVERY` absent | ✅ 15 passed | ✅ 4 cases (idempotent zero-call/no-row-change, interrupted+resume, `stopped=limit`, batch log 1/2 + 2/3) | ✅ `_log_progress` extracted |
| 4.5–4.6 (4c) | `tests/test_classify_catalog.py` | Integration | ✅ 15/15 focused | ✅ bound constants absent (5 failed) | ✅ 21 passed | ✅ 6 cases (env defaults, RPM gaps, wall stop+defer, per-run cap, limit overrides cap, continues-after-failure) | ✅ `_now`/`_sleep` seams; autouse no-op sleep keeps tests deterministic |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `python -m pytest -q tests/test_classify_catalog.py` → **21 passed in 0.09s** |
| Runtime harness command/scenario and exact result | `python -m jobs.classify_catalog --dry-run` against a temporary SQLite DB seeded with 1 product → **`dry-run pending=1 elapsed=0.0`** and **0** `editorial_decision` rows (zero provider calls, zero writes). The shadow run (`EDITORIAL_PROVIDER_API_KEY=…`) is CI-external and was not run in this worktree. |
| Rollback boundary | Delete `jobs/classify_catalog.py` + `tests/test_classify_catalog.py`. No production code imports the job yet (cron wiring is a deploy/Phase 7 concern); persisted decisions are inert while mode is `off`. |

### Deviations from Design

- `run`'s signature carries the full fixed contract (`limit`, `max_seconds`) from 4a, but `limit` is implemented in 4b and `max_seconds`/rate/cap in 4c; this is commit slicing, not a contract deviation.
- Clock seams `_now()` / `_sleep()` are module-level functions rather than injected parameters: the design fixes the `run` signature, so bounds are tested by monkeypatching the seams (a virtual clock shared by the job and the fake provider).
- The `item` dict passed to `classify_fn` is `{title, category, category_slug}` — the binding constraint requires the product's own `category_slug` for the provider's v1 context rule.
- Failure-not-cached holds by construction (a decision is written only from a validated, non-`None` result); the "job continues after a failed product" assertion validates that by-construction behavior rather than a fresh RED.
- Per-run cap reason is `limit` when the explicit `--limit` triggers and `max_products` when the configured `EDITORIAL_JOB_MAX_PRODUCTS` triggers; an explicit `limit` overrides the configured cap.

### Issues Found

None. All 230 baseline tests remain green with no semantic modification (full suite: 251 passed).

### Commits (4a / 4b / 4c re-slice)

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `1fe5481` | `feat(curation): run incremental catalog classification with failure-not-cached decisions` | `jobs/classify_catalog.py`, `tests/test_classify_catalog.py` | 334 (< 400) |
| `0159a0e` | `feat(curation): commit classification decisions in batches with a resumable run limit` | `jobs/classify_catalog.py`, `tests/test_classify_catalog.py` | 110 (< 400) |
| `36c2506` | `feat(curation): bound classification runs by rate, wall time, and product cap` | `jobs/classify_catalog.py`, `tests/test_classify_catalog.py` | 159 (< 400) |
| this artifacts commit | `docs(sdd): track curacion-regalos-ia openspec artifacts` | `openspec/**` | artifacts |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main); **PR 4 split into PR 4a + PR 4b + PR 4c** to fit the 400-line review budget.
- Work unit 4a: incremental selection + dry-run + valid-only persistence + CLI — **334 authored lines**.
- Work unit 4b: batched commits (`EDITORIAL_JOB_COMMIT_EVERY`) + resumable `limit` + progress logs — **110 authored lines**.
- Work unit 4c: rate/wall/per-run bounds + `stopped=reason` — **159 authored lines**.
- Boundary: starts after the Phase 3 `curation_provider.py` adapter; ends with the standalone job + its 21 tests. No cron wiring yet (deploy/Phase 7).
- Review budget: every slice is under 400 authored lines and each was verified green independently (`python -m pytest -q tests/test_classify_catalog.py`).

### Status

8/8 Phase 4 tasks complete across PR 4a (`1fe5481`, 334), PR 4b (`0159a0e`, 110) and PR 4c (`36c2506`, 159). Ready for next batch (Work Unit 5 / PR 5 — `jobs/evaluate_curation.py`).

---

## Batch: Work Unit 5 / PR 5 — Phase 5: Evaluation Gate (`jobs/evaluate_curation.py`)

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 5 targets the PR 4 slice)
**Status:** Complete — 3/3 Phase 5 tasks. Ready for next batch (Work Unit 6 / PR 6).

**Re-slice note (review budget):** Work Unit 5 landed as **three** stacked
commits, each a cohesive behavior under the 400-line budget: **5a** the
stratified sample and the human-labels contract, **5b** the offline metric math,
and **5c** the single-row gate upsert plus CLI wiring and the enforce-precondition
join. No tests or code were removed to fit the budget.

### Completed Tasks

- [x] 5.1 RED — `tests/test_curation_gate.py`: deterministic category-stratified `sample_products`; `evaluate` metric math (pass at 92% agreement / ~3% excluded-leak / 8% unknown / 100% coverage; fail at 87% agreement; fail at 8% leak; fail at 97% coverage; pass-with-`unknown`-flag at 14%); malformed/partially-filled labels rejected; successful run upserts exactly one gate row; zero provider calls.
- [x] 5.2 GREEN — `jobs/evaluate_curation.py`: `sample_products`, `evaluate`, `GateReport`, `run(session, labels_path=None, sample_out=None, log=print)`, `main(argv=None, session=None)`, label-template output, single-row `EditorialGateState` upsert.
- [x] 5.3 Verify — a passing gate row with `coverage_ratio == 1.0` and the current `policy_version` makes `curation.effective_filter_mode` return `enforce`; an incomplete-coverage gate keeps it `off`.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `jobs/evaluate_curation.py` | Created | Offline gate harness: `LabelsError`, `GateReport`, threshold constants, `sample_products`, `_load_labels`, `evaluate`, `_upsert_gate`, `_build_template`/`_emit_template`, `run`, `_parse_args`, `main`. Reads persisted decisions + a labels file; makes zero provider calls; coverage reuses `curation.pending_products` so backfill completeness cannot drift. |
| `tests/test_curation_gate.py` | Created | 26 tests: stratified deterministic sampling (3), labels contract (5), threshold constants, five spec metric scenarios, offline (evaluate + run), single-row upsert + re-run update, malformed/partially-filled exit 1 with no write, template output, CLI parse + injected-session `main`, and the two enforce-precondition join tests. |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 5 tasks 5.1–5.3 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 5.1 (5a) | `tests/test_curation_gate.py` | Unit | ✅ 251/251 full suite | ✅ `ModuleNotFoundError: jobs.evaluate_curation` | ✅ 9 passed | ✅ 9 cases (round-robin spread + determinism, cap-at-available, inactive excluded, well-formed parse, unparseable JSON, empty entries, blank state, out-of-enum state, missing asin) | ✅ strata ordered deterministically; `_load_labels` validation extracted |
| 5.1 (5b) | `tests/test_curation_gate.py` | Unit | ✅ 9/9 focused | ✅ `no attribute 'evaluate'` (7 failed) | ✅ 16 passed | ✅ 12 cases (threshold constants; 5 metric scenarios incl. 92/3/8/100, 87% agreement, 8% leak, 97% coverage, 14% unknown-flag; offline sentinel; model/policy/labeled_count) | ✅ coverage reuses `pending_products`; `_decisions_by_product` helper |
| 5.2/5.3 (5c) | `tests/test_curation_gate.py` | Integration | ✅ 16/16 focused | ✅ `no attribute 'run'/'main'/'_parse_args'` (10 failed) | ✅ 26 passed | ✅ 10 cases (exactly-one-row upsert + fields/naive timestamp, re-run updates same row, malformed exit 1 no write, partially-filled exit 1 no write, template output no write, run offline, passing-gate → enforce, incomplete-coverage → off, CLI parse, injected-session main) | ✅ `_upsert_gate` created/updated branches |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `python -m pytest -q tests/test_curation_gate.py` → **26 passed in 0.33s**; `python -m pytest -q tests/test_curation_gate.py -k precondition` → **2 passed, 24 deselected** |
| Runtime harness command/scenario and exact result | `DATABASE_URL=sqlite:///<tmp>/gate.db python -m jobs.evaluate_curation --sample-out <tmp>/sample.json` against a temp SQLite DB seeded with 3 products (2× `hogar`, 1× `electronica`) → **`sample=3 written=<tmp>/sample.json`**, exit 0; the template round-robin listed `A2` (electronica) then `A0`, `A1` (hogar), each `expected_state=""`. No provider call. |
| Rollback boundary | Delete `jobs/evaluate_curation.py` + `tests/test_curation_gate.py` and revert the Phase 5 lines in `tasks.md`. Nothing imports the gate; `DELETE FROM editorial_gate_state` returns `effective_filter_mode` to `off`. |

### Deviations from Design

- `GateReport` carries two fields beyond the design's implied set — `unknown_flagged` (the SHOULD-threshold warning) and `labeled_count`. Both are read-only reporting values; the persisted row keeps exactly the nine designed columns.
- `coverage_ratio` is computed as `(active - pending) / active` reusing `curation.pending_products` rather than re-deriving fingerprint matching, so backfill completeness is defined identically to the classification job and cannot drift.
- `unknown_ratio` and `coverage_ratio` are measured across **all active products** (per the spec wording "across active products after backfill"), while agreement/leak are measured over the human-labeled sample. In the tests the active set equals the seeded catalog.
- The human-labels file format is a JSON object `{"policy_version", "labels": [{"asin", "expected_state"}]}`. A blank `expected_state` is a partially-filled file and is rejected; `_load_labels` raises `LabelsError`, which `run` catches to return exit 1 **before** any write.
- The `sample_products` template also carries `"policy_version"` so the operator sees which policy the labels are for; `evaluate` does not require it.

### Issues Found

None. All 251 baseline tests remain green with no semantic modification (full suite: 277 passed).

### Commits (5a / 5b / 5c re-slice)

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `c4d4dcf` | `feat(curation): stratify the evaluation sample and validate the human-labels file` | `jobs/evaluate_curation.py`, `tests/test_curation_gate.py` | 222 (< 400) |
| `e0f120c` | `feat(curation): compute the evaluation-gate metrics against human labels` | `jobs/evaluate_curation.py`, `tests/test_curation_gate.py` | 276 (< 400) |
| `53b852f` | `feat(curation): persist the evaluation verdict and wire the gate CLI` | `jobs/evaluate_curation.py`, `tests/test_curation_gate.py` | 263 (< 400) |
| `ad1e853` | `test(curation): name the gate tests for the task 5.3 precondition selector` | `tests/test_curation_gate.py` | small test-only rename |
| this artifacts commit | `docs(sdd): track curacion-regalos-ia openspec artifacts` | `openspec/**` | artifacts |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main); **PR 5 split into PR 5a + PR 5b + PR 5c** to fit the 400-line review budget.
- Work unit 5a: `sample_products` + `LabelsError` + `_load_labels` — **222 authored lines**.
- Work unit 5b: threshold constants + `GateReport` + `_decisions_by_product` + `evaluate` — **276 authored lines**.
- Work unit 5c: `_upsert_gate` + template output + `run`/`main`/CLI — **263 authored lines**.
- Boundary: starts after the Phase 4 classification job; ends with the standalone offline gate + its 26 tests. No consumer wired (the gate's verdict is read by `curation.effective_filter_mode`, already covered by Phase 2).
- Review budget: every slice is under 400 authored lines and each was verified green independently (`python -m pytest -q tests/test_curation_gate.py`).

### Status

3/3 Phase 5 tasks complete across PR 5a (`c4d4dcf`, 222), PR 5b (`e0f120c`, 276) and PR 5c (`53b852f`, 263). Ready for next batch (Work Unit 6 / PR 6 — centralized filtering wiring).

---

## Batch: Work Unit 6 / PR 6 — Phase 6: Centralized Filtering Wiring

**Mode:** Strict TDD
**Delivery:** auto-chain / stacked-to-main (PR 6 targets the PR 5 slice)
**Status:** Complete — 7/7 Phase 6 tasks. Ready for next batch (Work Unit 7 / PR 7).

**Re-slice note (review budget):** Work Unit 6 landed as **three** stacked
commits, each a cohesive behavior under the 400-line budget: **6a** the
mode-gated catalog predicate + category suppression + the strict-TDD test
infrastructure (T1 shadow structural proof), **6b** the `/ideas` context
pass-through and the curation-aware blog empty state (route/blog/safety tests),
and **6c** the T2 golden-baseline lock (9 generated snapshots + the assertion
test). No tests or code were removed to fit the budget; the generated goldens
are excluded from the authored count per the work-unit-commits skill.

### Completed Tasks

- [x] 6.1 RED — default `off`; `--editorial-update-baselines` option + `seed_editorial`, `sql_statements`, `editorial_update_baselines` fixtures in `tests/conftest.py`; T1 structural (no editorial SQL under `off`) and byte-identical-with-vs-without-decision-rows tests.
- [x] 6.2 GREEN — `CatalogQuery.editorial_context`; `search_products` appends the shared-filter predicate before the count (mode-gated); `list_categories` filters to `visible_category_slugs` under `enforce`.
- [x] 6.3 RED — `enforce` general/context/excluded/unknown visibility; filtered totals + page-2 tail; all shared surfaces hide the excluded product; `/ideas` context merge.
- [x] 6.4 GREEN — `_catalog_context(..., editorial_context=)` + `/ideas/{category_slug}` pass-through in `main.py`; explicit non-empty hero guard in `services.py`; curation-aware empty state in `templates/blog_post.html`.
- [x] 6.5 RED/GREEN — zero-visible category suppressed from `list_categories` and `/sitemap.xml` (sitemap inherits, no code change); unchanged under `off`; blog empty state + hero fallback; wish list unaffected (add excluded product + existing wishes survive); `refresh_catalog.baseline_counts` counts unfiltered `ProductList` and curation never mutates it.
- [x] 6.6 T2 — 9 golden `tests/baselines/editorial_off_<surface>.html` snapshots generated with `--editorial-update-baselines` under `off` + byte-for-byte assertion test.
- [x] 6.7 Verify — focused suite green; full suite green with no semantic modification to existing tests.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `catalog.py` | Modified | `CatalogQuery.editorial_context`; `search_products` computes `editorial_visibility(session)` and appends `context_category(slug)` on the context surface else the unchanged category filter + `general()`, all into the shared `filters` list **before** `count`; `list_categories` filters to `visible_category_slugs(session)` under `enforce` (None ⇒ unchanged). |
| `main.py` | Modified | `_catalog_context` gains `editorial_context` and forwards it into `CatalogQuery`; `/ideas/{category_slug}` passes `editorial_context=category_slug`. Sitemap untouched (renders `list_categories`). |
| `services.py` | Modified | `get_blog_post_detail`: hero fallback restructured to an explicit non-empty-list guard (`if products and not post.get("hero_image")`); pagination already flows through the filtered `search_products`. |
| `templates/blog_post.html` | Modified | Curation-aware empty state (stable "No encontramos productos" phrase + catalog link) for when filtering empties the list. |
| `tests/conftest.py` | Modified | `pytest_addoption` for `--editorial-update-baselines`; `editorial_update_baselines`, `sql_statements` (`before_cursor_execute` capture), and `seed_editorial` fixtures. |
| `tests/test_editorial_filtering.py` | Created | 28 tests: default off; T1 structural + byte-identical; enforce visibility/totals/pagination; category + sitemap suppression; route surfaces incl. dashboard; `/ideas` context merge; blog empty/hero; wish + ProductList safety rails; T2 golden baselines. |
| `tests/baselines/` | Created | 9 generated `editorial_off_<surface>.html` snapshots (home, catalog, catalog_category, trends, most_desired, bestsellers, ideas, blog, sitemap). |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 6 tasks 6.1–6.7 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 6.1 (6a) | `tests/test_editorial_filtering.py` | Integration | ✅ 277/277 full suite | ✅ `fixture 'seed_editorial' not found` + enforce failures (20 failed, 8 passed) | ✅ offline/T1 green | ✅ 3 cases (default off, no-editorial-SQL capture, byte-identical with/without rows) | ✅ fixtures extracted to `conftest.py` |
| 6.2–6.3 (6a) | `tests/test_editorial_filtering.py` | Integration | ✅ 277/277 | ✅ 20 failed pre-wiring | ✅ 9 passed | ✅ 9 cases (eligible-only, contextual matcher + general hide, excluded/unknown hidden, totals 12/3, page-2 tail, list_categories suppress + off) | ✅ predicate helpers reused from `curation` |
| 6.4–6.5 (6b) | `tests/test_editorial_filtering.py` | Integration | ✅ 9/9 focused | ✅ route/context/blog tests failed pre-wiring | ✅ 19 passed | ✅ 10 cases (2 sitemap, dashboard, all-surfaces, ideas merge, blog empty + hero, wish add, wish survive, ProductList immutable) | ✅ hero guard expressed as `products and not ...` |
| 6.6 (6c) | `tests/test_editorial_filtering.py` | Regression (T2) | ✅ 19/19 focused | ✅ missing baseline (RED) | ✅ 28 passed after `--editorial-update-baselines` | ✅ 9 surfaces | ➖ None needed |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `python -m pytest -q tests/test_editorial_filtering.py` → **28 passed in 1.2s**; `python -m pytest -q --ignore=tests/test_e2e.py` → **305 passed in 6.5s** |
| Runtime harness command/scenario and exact result | Real FastAPI app through `TestClient`: `/`, `/catalog`, `/catalog?category=…`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, `/blog/{slug}`, `/sitemap.xml`, `/dashboard`, `/wishes` exercised under `off` and `enforce`. `--editorial-update-baselines` regenerated the 9 `tests/baselines/editorial_off_*.html` snapshots; a normal run then matched them byte-for-byte (9 passed). T1 captured the executed SQL via `before_cursor_execute` and proved zero editorial-table references under `off`. |
| Rollback boundary | Primary = config flip (`EDITORIAL_FILTER_MODE=off`, or `DELETE FROM editorial_gate_state`) — no code revert; persisted decisions become inert. Reverting the three commits (`3c53dbb`, `dd6d1fa`, `ebaf737`) plus deleting `tests/baselines/` restores the pre-wiring code with no unrelated change. |

### Deviations from Design

- `services.py` required no behavior change for correctness: `get_blog_post_detail` already paginates over `search_products` (now filtered) and already guarded the hero on product truthiness. The edit makes the "never derived from an empty list" contract explicit (`if products and not post.get("hero_image")`) and documents the filtered-set flow. The template's empty state was already graceful; it is now curation-aware (updated copy + catalog link) while keeping a stable testable phrase.
- `list_categories` calls `visible_category_slugs(session)` and `search_products` independently calls `editorial_visibility(session)`, so an `enforce` catalog page performs two small gate reads instead of one. This mirrors design Decision 8 ("one tiny SELECT per `search_products`/`list_categories` call") and keeps the two paths decoupled; the `off` path still performs zero reads.
- The T1 byte-identical test compares responses within the same test (decision rows absent vs present) rather than against a stored pre-change capture; this is the data-independence proof Decision 4 specifies, and T2 supplies the separate pre-change drift lock.

### Issues Found

None. All 277 pre-existing tests remain green with no semantic modification (full suite: 305 passed = 277 + 28 new).

### Commits (6a / 6b / 6c re-slice)

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `ebaf737` | `feat(curation): gate catalog search and category listing with editorial visibility` | `catalog.py`, `tests/conftest.py`, `tests/test_editorial_filtering.py` | 327 (< 400) |
| `dd6d1fa` | `feat(curation): route the ideas context and make the blog empty state curation-aware` | `main.py`, `services.py`, `templates/blog_post.html`, `tests/test_editorial_filtering.py` | 184 (< 400) |
| `3c53dbb` | `test(curation): lock the off-mode surfaces with golden baselines` | `tests/test_editorial_filtering.py`, `tests/baselines/` | 38 authored + 9 generated goldens (excluded) |
| this artifacts commit | `docs(sdd): track curacion-regalos-ia openspec artifacts` | `openspec/**` | artifacts |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main); **PR 6 split into PR 6a + PR 6b + PR 6c** to fit the 400-line review budget.
- Work unit 6a: predicate insertion + `list_categories` suppression + T1 test infra/tests — **327 authored lines**.
- Work unit 6b: `/ideas` context wiring + blog empty state + route/blog/safety tests — **184 authored lines**.
- Work unit 6c: T2 golden baselines + assertion test — **38 authored lines** (+ generated snapshots).
- Boundary: starts after the Phase 5 evaluation gate; ends with every public product surface (catalog/trends/desired/bestsellers/ideas/blog/dashboard), navigation, and the sitemap filtered under `enforce` and provably unchanged under `off`. First production consumers of `curation.editorial_visibility` / `visible_category_slugs`.
- Review budget: every slice is under 400 authored lines and each was verified green independently (`python -m pytest -q tests/test_editorial_filtering.py`).

### Status

7/7 Phase 6 tasks complete across PR 6a (`ebaf737`, 327), PR 6b (`dd6d1fa`, 184) and PR 6c (`3c53dbb`, 38 + goldens). Ready for next batch (Work Unit 7 / PR 7 — config/env docs, runbook, final verification).

---

## Batch: Work Unit 7 / PR 7 — Phase 7: Config/Env Docs, Runbook, Final Verification

**Mode:** Strict TDD (docs-only slice — no behavior change, no RED test required)
**Delivery:** auto-chain / stacked-to-main (PR 7 targets the PR 6 slice)
**Status:** Complete — 3/3 Phase 7 tasks. **All 7 work units / 42 tasks complete. Ready for archive.**

**Slice note (review budget):** Phase 7 is documentation only. It landed as a
**single** docs commit (`README.md` + the new rollout runbook, **218 authored
lines < 400**), because the README section and the runbook cross-reference each
other — splitting them would leave a commit pointing at a file the next commit
adds, violating work-unit commit coherence. No application code changed.

### Completed Tasks

- [x] 7.1 Document all env vars — the runbook's "Environment variables" table
  covers all **8** `os.getenv` reads with defaults and purpose, and explicitly
  separates the two **non-env code constants** (`EDITORIAL_POLICY_VERSION`,
  `EDITORIAL_CONTEXTS`); the README quick list mirrors it.
- [x] 7.2 Deployment/rollout runbook — rollout sequence (migration → shadow
  backfill → evaluation gate → enable `enforce`), the exact `enforce`
  precondition, both Railway cron entries with the restart-loop caveat, the
  migration step integrated by reference to the existing migration runbook (not
  duplicated), and rollback (`EDITORIAL_FILTER_MODE=off` / `DELETE FROM
  editorial_gate_state`).
- [x] 7.3 Final verification — full suite green; the shadow `off` default changed
  no existing behavior.

### Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `README.md` | Modified | Added the editorial vars to the `.env` example; new "Curación editorial del catálogo (servicios cron)" subsection: the two cron services, the restart caveat, the env-var quick table, and a link to the runbook. |
| `docs/deploy/2026-10-04-curacion-regalos-ia-rollout-runbook.md` | Created | Full operator runbook: components, env-var reference (8 vars + 2 constants), Railway cron setup for `jobs.classify_catalog` / `jobs.evaluate_curation`, restart-loop caveat, migration step (by reference), 4-phase rollout, exact `enforce` precondition, rollback, verification. |
| `openspec/changes/curacion-regalos-ia/tasks.md` | Modified | Marked Phase 7 tasks 7.1–7.3 `[x]`. |

### TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 7.1–7.2 | N/A — docs only | N/A | ✅ 305/305 full suite | N/A (no production code; `Do NOT change application behavior`) | N/A — docs | N/A | ✅ README/runbook cross-referenced to avoid duplication |
| 7.3 | `tests/` (full suite) | Regression | ✅ 305/305 baseline | N/A — verification task | ✅ 305 passed | N/A | ➖ None needed |

### Work Unit Evidence

| Evidence | Value |
|---|---|
| Focused test command and exact result | `python -m pytest -q --ignore=tests/test_e2e.py` → **305 passed in 6.47s** (identical to the pre-change baseline; docs-only slice) |
| Runtime harness command/scenario and exact result | **N/A — docs-only, no runtime boundary.** The documented variable names were confirmed against the code with `grep -rn 'os.getenv("EDITORIAL' curation.py curation_provider.py jobs/classify_catalog.py` → 8 matches (7 one-line + `EDITORIAL_PROVIDER_BASE_URL` across its multi-line call), matching the runbook table exactly. |
| Rollback boundary | Revert `README.md` and delete `docs/deploy/2026-10-04-curacion-regalos-ia-rollout-runbook.md`. Documentation only; zero behavior change, no code to revert. |

### Deviations from Design

- The scope prompt grouped `EDITORIAL_POLICY_VERSION` and `EDITORIAL_CONTEXTS`
  under "env vars", but the code reads them as **module constants**, not
  `os.getenv`. Documented them as policy constants (in a clearly separate
  section) to keep the docs truthful; the verification grep confirms only 8
  `os.getenv("EDITORIAL…")` reads exist. This is an honesty correction, not a
  behavior deviation.
- The runbook is written in English to match its sibling
  `docs/deploy/…migration-runbook.md`; the README additions are in Spanish to
  match the README's existing convention.

### Issues Found

None. Full suite 305 passed, unchanged from the Phase 6 baseline; no application
behavior modified.

### Commits

| Hash | Message | Files | Authored lines |
|------|---------|-------|----------------|
| `df37ba7` | `docs(curation): document the editorial curation rollout and rollback runbook` | `README.md`, `docs/deploy/…rollout-runbook.md` | 218 (< 400) |
| this artifacts commit | `docs(sdd): track curacion-regalos-ia openspec artifacts` | `openspec/**` | artifacts |

### Workload / PR Boundary

- Mode: chained PR slice (stacked-to-main).
- Work unit 7: config/env docs + rollout runbook + final verification — **218 authored lines (< 400)**.
- Boundary: starts after the Phase 6 filtering wiring; ends with the operator documentation and a green full suite. No code change.

### Status

3/3 Phase 7 tasks complete in commit `df37ba7` (218 authored lines). **All 7 work units / 42 tasks complete; full suite 305 green. Ready for archive.**
