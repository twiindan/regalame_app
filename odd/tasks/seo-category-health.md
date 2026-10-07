# SEO category health: real 404s and page-specific canonicals on `/ideas/{slug}`

Roadmap item 1 of the persisted roadmap `seo/next-improvements-roadmap` (Engram #932). This is the only ODD planning artifact for this feature.

## Objective, problem, and why

`/ideas/{category_slug}` currently accepts any slug, always marks the page indexable (`always_indexable=True`), and clamps out-of-range pages. An unknown slug returns a `200` soft-404 with a canonical pointing at the invalid URL, and every `?page=N`/filtered variant stays indexable. This creates soft-404s and parameter-URL index bloat.

This is a deliberate, user-approved reversal of the design in `docs/superpowers/specs/2026-09-27-catalogo-navegable-design.md` (L164/L205 clamp, L207 empty-without-redirect, L179 canonical-to-clean-URL). The user selected the **strict** policy on 2026-10-07.

## Authorized scope and current boundary

- Authorized: local implementation, strict TDD, tests, updated minimal 404 template, design-doc amendment, one work-unit commit on `feature/seo-category-health`.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Base: `main` at `27dfdfd`. Branch `feature/seo-category-health` created before the first feature write. The unrelated `feature/search-console-oauth` WIP is stashed as `stash@{0}` and must not be touched.
- `feature/seo-dual-landings` (2 commits) is NOT merged into `main`; out of scope here.

## Approved policy (strict)

| Case | Behavior |
| --- | --- |
| `/ideas/{slug}` slug not in visible categories (`list_categories`) | **404** real |
| `?page` non-integer, `< 1`, or `> total_pages` | **404** real |
| `?page=N` with `N > 1` in range | `200`, canonical = **self** (`/ideas/{slug}?page=N`), keep `rel="prev"`/`rel="next"` |
| `/ideas/{slug}` page 1 | `200`, canonical = `/ideas/{slug}` |
| "Valid" slug definition | slug present in `list_categories(session)` (editorially visible set, same source as sitemap/nav) |

Consequence accepted by the user: under editorial `enforce`, a category with zero visible products 404s instead of rendering an empty page.

## Constraints

- Scope is `/ideas/{category_slug}` **only**. `/catalog`, `/bestsellers`, `/trends`, `/most-desired` keep the existing clamp behavior and tests.
- No global 404 exception handler; the 404 is route-local to avoid changing other routes' bodies.
- Keep Jinja2 + HTMX; no new dependencies; no Node/bundler. Keep the pinned requirements baseline.
- Business logic stays in `catalog.py`/`services.py`; routes stay thin (`openspec/config.yaml` design rules).
- 404 responses MUST use HTTP status `404` and MUST NOT emit a canonical pointing at the invalid URL.
- HTMX requests to an invalid `/ideas` URL must also get status `404` (no soft success).

## Files

- `main.py` — validation + overflow + canonical in `category_seo_page` (~415-440); strict page parsing helper.
- `templates/404.html` — **new**, minimal, extends `base.html`, `noindex` meta.
- `tests/test_catalog_routes.py` — flip the unknown-slug test; update pagination canonical test; add overflow/invalid-page tests.
- `docs/superpowers/specs/2026-09-27-catalogo-navegable-design.md` — dated amendment + corrected rows (extend in Spanish, matching the existing doc).
- `odd/tasks/seo-category-health.md` — this document.
- Baselines `tests/baselines/*.html`: expected unchanged (page-1 canonical and catalog noindex stay the same). Regenerate only if a real diff appears.

## Task checklist and acceptance

### T1 — Implement strict 404 + page-specific canonical as one work unit

- [x] **T1**: Deliver the behavior with tests and the 404 template together (strict red → green → refactor).

Acceptance (Given/When/Then):

- Given a slug not in `list_categories`, When `GET /ideas/inexistente`, Then status `404` and body has no `rel="canonical"` for that URL.
- Given a valid category with `total_pages = 2`, When `GET /ideas/{slug}?page=3`, Then status `404`.
- Given a valid category, When `GET /ideas/{slug}?page=99`, Then status `404`.
- Given a valid category, When `GET /ideas/{slug}?page=0` or `?page=abc`, Then status `404`.
- Given a valid category with 2+ pages, When `GET /ideas/{slug}?page=2`, Then status `200` and `<link rel="canonical" href="/ideas/{slug}?page=2">`, with `rel="prev"` present.
- Given a valid category, When `GET /ideas/{slug}`, Then status `200` and `<link rel="canonical" href="/ideas/{slug}">`.
- Given editorial `enforce` and a category with zero visible products, When `GET /ideas/{zero-visible}`, Then status `404`.
- Given a valid category with products, When `GET /ideas/{slug}`, Then status `200` and products render (regression).
- Given `GET /ideas/{slug}` with `HX-Request: true` and valid slug, Then `200` partial (unchanged).

Required existing test changes (explicit, not hidden):

- `tests/test_catalog_routes.py::test_ideas_unknown_slug_is_empty_not_redirect` (L67-69) → becomes a 404 assertion (rename accordingly).
- `tests/test_catalog_routes.py::test_ideas_slug_canonical_and_pagination_links` (L95-114) → page 2 canonical becomes `/ideas/electronica?page=2`.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`). Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_catalog_routes.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python -m pytest -q --editorial-update-baselines tests/test_editorial_filtering.py   # ONLY if a baseline diff is intended
```

## Review workload and delivery

| Work unit | Forecast authored additions + deletions |
| --- | ---: |
| T1 implementation + 404 template + tests + design amendment + this doc | ~150-260 |

- **Delivery default: `ask-on-risk`.** Forecast is under the 400-line advisory; no split or exception needed.
- RDD status to be read before commit; if enabled, run the native candidate assessment after the work-unit commit.

## Rollback

Revert the T1 commit on `feature/seo-category-health`; delete the branch. `templates/404.html` is additive. No production data, credentials, or other routes affected. Restore the stashed search-console WIP with `git stash pop --index` only if the user asks.

## Progress

- [x] Stashed search-console WIP as `stash@{0}`; created `feature/seo-category-health` from `main` (`27dfdfd`).
- [x] Mapped scope (read-only) and confirmed existing tests/design doc.
- [x] Policy decided by user: **strict**.
- [x] T1 implemented under strict TDD and committed as `fdf7b6e`.

### Verification evidence (2026-10-07)

- RED (before implementation): `tests/test_catalog_routes.py` 6 failed / 20 passed; `test_editorial_filtering.py::test_ideas_zero_visible_category_returns_404` 1 failed (200 != 404).
- GREEN focused: `venv/bin/python -m pytest -q tests/test_catalog_routes.py` → **28 passed**.
- GREEN regression: `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py` → **343 passed**.
- Parent spot check re-ran both: focused **28 passed**, full **343 passed**. `git diff --check` clean.
- Golden baselines untouched (page-1 canonical and catalog noindex unchanged).
- Authored additions + deletions: **131** (121 additions, 10 deletions) — under the 400 advisory.

### Native review (RDD, global on)

- Assess: `risk: medium` (executable change in `main.py`), 5 paths, 131 lines.
- START granted by user; one lens `review-reliability`; outcome **approved**; acknowledgement burned (`gentle-ai.review-acknowledged/v1`, `authority: burned`).
- Non-blocking advisory findings from the T1 review:
  - R3-1 WARNING `main.py:246` — `int(value)` is lenient (`?page=%202%20`, `?page=1_0`, `?page=+2`, non-ASCII digits parse), so some non-canonical page URLs return 200 with a normalized canonical instead of 404. **Addressed in T2.**
  - R3-2 SUGGESTION `main.py:463-465` — explicit `?page=1` canonical not asserted by a test.
  - R3-3 SUGGESTION `main.py:453-457` — HTMX invalid requests get a full-document 404 (matching HTMX no-swap-on-4xx default) rather than a fragment.

### T2 — Harden page parsing (fixes R3-1)

- [x] **T2**: `_parse_page_number` now accepts only ASCII digits (`[0-9]+`). Committed as `fc6a8ef`.

Verification:

- RED: 12 failed / 6 passed (`-k "parse_page_number or lenient_integer or empty_returns_404"`), including in-range representatives (`" 1 "`, `"+1"`, `"0_1"`, fullwidth `１`) that returned 200 under the old lenient `int()`.
- GREEN focused: `venv/bin/python -m pytest -q tests/test_catalog_routes.py` → **46 passed**; regression `--ignore=tests/test_e2e.py` → **361 passed**.
- Native review (base `96db766`): `medium`, 3 paths, 58 lines; lens `review-reliability`; **approved**; acknowledgement burned.
- New non-blocking advisory finding from the T2 review:
  - R3-001 WARNING `main.py:248` — removing the base `try/except` made the helper non-total: a `page` value of >4300 ASCII digits passes `isascii()/isdigit()` and then `int(value, 10)` raises `ValueError` (CPython 3.11+ `int_max_str_digits`), turning a former deterministic 404 into an unhandled error. **Addressed in T3.**

### T3 — Restore parser totality (fixes R3-001)

- [x] **T3**: `int(value, 10)` is wrapped in `try/except ValueError` → `None`, so an over-long digit string is invalid rather than raising. Committed as `ef1e4a0`.

Verification:

- RED: `-k over_long` → **2 failed** (unhandled `ValueError: Exceeds the limit (4300 digits)` from the helper and the route).
- GREEN focused: `venv/bin/python -m pytest -q tests/test_catalog_routes.py` → **48 passed**; regression `--ignore=tests/test_e2e.py` → **363 passed**.
- Native review (base `286d6b2`): `medium`, 2 paths, 24 lines; lens `review-reliability`; **approved**; acknowledgement burned. Transport note: the OpenCode reviewer result needed a retry after an initial `opencode_reviewer_result_refused`; the slot was reoffered by STATUS and the second relaunch captured.
- New non-blocking advisory finding from the T3 review:
  - R3-over-long-digit-test-version-dependent WARNING `tests/test_catalog_routes.py:122-126` — the unit assertion hard-codes the CPython 3.11+ digit cap; on an interpreter without it (or with the cap raised ≥5000) `int()` succeeds and the helper returns a large int, so the `is None` assertion would fail. The route-level test stays correct across interpreters. Candidate follow-up: make the assertion cap-independent (assert "no error escapes" / use a monkeypatched cap) or drop the unit test in favour of the route test.

## Next step

T1–T3 are implemented, verified, and reviewed (approved/burned). Remaining is user-owned delivery: push and PR are NOT authorized and were not performed. Open follow-ups: R3-over-long-digit-test-version-dependent, R3-2, R3-3; restore `stash@{0}` when returning to search-console; roadmap item 2 next. `feature/seo-dual-landings` (2 commits) remains unmerged into `main`.
