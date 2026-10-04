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
