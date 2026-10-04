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
