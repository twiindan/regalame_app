# Archive Report: `curacion-regalos-ia`

**Archived**: 2026-10-04
**Branch**: `feat/curacion-regalos-ia`
**Artifact store**: hybrid (OpenSpec files + Engram, project `regalame_app`)
**Archived to**: `openspec/changes/archive/2026-10-04-curacion-regalos-ia/`

## Summary

AI-assisted, offline gift-suitability classification of catalog products plus a centralized,
mode-gated editorial filter across public product surfaces. Delivered behind the default `off`
(shadow) mode: no public behavior changes until `enforce` is enabled after the evaluation gate
passes with 100% coverage.

## Final State (authority-ranked)

| Fact | Value | Source (rank) |
|------|-------|---------------|
| Tasks complete | **40 / 40**, 0 unfinished (`tasks.md` has exactly 40 `[x]` items) | Persisted tasks artifact (rank 1) |
| Full test suite | **305 passed**, no regressions from the 128-test baseline | Launch final-state facts (rank 2) |
| Filter mode default | `off` (shadow) — zero public behavior change; `enforce` gated by evaluation pass + 100% coverage | Launch facts (rank 2) |
| Delivery | **NOT pushed, NO PR opened, NO merge** — delivery is the user's decision | Launch facts (rank 2) |
| SDD verification | **Not run** — no `verify-report` was produced | Launch facts (rank 2) |
| Migration | `b3d9f1a7c250`, chained from `9f1c7b2a4d3e`; manual Postgres verification is a deploy-time runbook step | Launch facts (rank 2) |
| Provider claims | `json_schema` support, quality, and cost remain **unproven** until the ~100-product evaluation gate runs | Launch facts (rank 2) |

## Source Contradictions (recorded, not silently resolved)

- `apply-progress.md` and the Engram tasks observation (`#832`) state **"42/42 tasks"**. The
  persisted `tasks.md` artifact contains exactly **40** checked task items and **0** unchecked.
  Per the Final-State Authority hierarchy the persisted tasks artifact outranks the intermediate
  snapshot, so the reported count is **40/40**; the "42" claim is a stale snapshot count.
- The design's `effective_filter_mode` snippet omits the `coverage_ratio == 1.0` clause. Per
  `apply-progress.md` this was a deliberate implementation addition (task 2.6, matching the
  `catalog-editorial-filtering` spec "Enforce with incomplete backfill behaves as off"). Recorded
  as a design-vs-implementation deviation already disclosed by the implementation, not an
  unresolved defect.

## Specs Synced

Both capabilities are NEW (the OpenSpec spec store held only `.gitkeep`), so each delta spec is a
full spec and was copied **mechanically** (shell `cp` → `diff -r` readback → `mv`), never routed
through a model Read/Write.

| Capability | Action | Requirements | Scenarios | Destination |
|------------|--------|--------------|-----------|-------------|
| `product-editorial-classification` | Created | 9 | 26 | `openspec/specs/product-editorial-classification/spec.md` |
| `catalog-editorial-filtering` | Created | 8 | 22 | `openspec/specs/catalog-editorial-filtering/spec.md` |

All delta content is additive (new capabilities); no REMOVED/RENAMED/MODIFIED sections exist, so
no destructive merge occurred. No existing spec required composition.

## Archive Contents

| Artifact | Status | Notes |
|----------|--------|-------|
| `proposal.md` | present | |
| `specs/product-editorial-classification/spec.md` | present | |
| `specs/catalog-editorial-filtering/spec.md` | present | |
| `design.md` | present | |
| `exploration.md` | present | |
| `tasks.md` | present | 40/40 complete, 0 unfinished; bytes preserved |
| `apply-progress.md` | present | intermediate snapshot; retained as historical record |
| `verify-report` | **absent** | SDD verification was not requested; no report was ever produced |

## Implementation State

- 7 work units complete, delivered as re-sliced stacked commits, each under the 400-line review
  budget where a behavioral change was involved.
- Public surfaces (`/catalog`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, blog
  lists, dashboard samples, sitemap) are provably unchanged under `off` (T1 structural proof +
  T2 golden baseline lock).
- Import pipeline (`scraper.py`, `catalog.import_from_json`) and wish lists are untouched.

## Verification

**Not run.** No `verify-report` exists for this change. The highest-ranked final-state evidence is
the launch prompt's reported suite result (305 passed). No verification certificate is claimed.

## Unresolved Findings / Risks

- **Provider claims unproven**: strict `json_schema` support, latency, rate, quality, and cost
  remain unverified in-repo until the ~100-product evaluation gate runs.
- **Migration not exercised by CI**: tests use `create_all`; the manual Postgres upgrade/downgrade
  runbook step is a deploy-time gate, not yet executed here.
- **Enforcement activation is pending**: `enforce` requires `gate_passed=true` AND
  `coverage_ratio == 1.0` AND a current policy version; the backfill and gate have not run, so the
  system ships inert (shadow) by design.
- **Residual `unknown` share** above the SHOULD threshold is a follow-up policy decision once gate
  data exists.

## Delivery

The branch is **not pushed** and **no PR was opened**. The change is committed locally on
`feat/curacion-regalos-ia` only; integration is intentionally left to the user.

## Engram Traceability

Observation IDs read/persisted for this change (project `regalame_app`):

- `#828` — `sdd/curacion-regalos-ia/explore`
- `#829` — `sdd/curacion-regalos-ia/proposal`
- `#830` — `sdd/curacion-regalos-ia/spec`
- `#831` — `sdd/curacion-regalos-ia/design`
- `#832` — `sdd/curacion-regalos-ia/tasks` (title carries the stale "42/42" count)
- `#833` — `sdd/curacion-regalos-ia/apply-progress` (title carries the stale "42" count)
- `#824` — `sdd-init/regalame_app`
- `#837` — session summary
- `sdd/curacion-regalos-ia/archive-report` — **this report** (persisted at archive time)
- `verify-report` — **not produced**

## Mechanical Readback Evidence

- Spec sync: `diff -r` between each delta spec and its staged temp copy — **empty (exit 0)** for
  both capabilities.
- Archive move: `git mv` of the change folder to the date-prefixed archive path, followed by
  `diff -r` of the pre-move recursive snapshot vs. the archived tree — **empty (exit 0)**.
