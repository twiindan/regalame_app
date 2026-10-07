# SEO low-risk indexing policy

Roadmap item 2 of the persisted roadmap `seo/next-improvements-roadmap` (Engram #932). This is the only ODD planning artifact for this feature.

## Objective, problem, and why

Three URL families currently have an unclassified or accidental indexing policy, which can leak duplicate or private URLs into search engines:

1. **`/join/{code}` (GET)** renders the group invitation page with the secret `code` in plain text and no `robots` directive; `robots.txt` does not disallow `/join/`. A secret invite token is crawler-exposed.
2. **Legacy catalog routes** (`/bestsellers`, `/trends`, `/most-desired`) are indexable at their clean URL, but the filter form and arbitrary query strings produce indexable duplicates with **no canonical** (`?source=…`, `?q=&sort=relevance&source=…`). `source` is *not* a bound query parameter on these routes, so the naive fix ("add `source` to the noindex rule") would wrongly de-index the three flagship landings because their `source` is always route-fixed and truthy.
3. **Public profiles** (`/p/{user_id}`) are indexable and actively submitted in the sitemap (up to 1000 users, exposing the user name and an `ItemList` JSON-LD of their gift list). Product decision made by the user on 2026-10-07: `noindex, follow` and remove from the sitemap.

Additionally the approved `/catalog` `noindex, follow` must be preserved.

## Authorized scope and current boundary

- Authorized: local implementation, strict TDD, tests, minimal template edits, a dated design-doc amendment, work-unit commits on `feature/seo-index-policy`.
- Not authorized: merge. Push and PR-to-main are performed at close per the user's instruction.
- Base: `main` at `edf2ab5` (== `origin/main`). Isolated worktree `…-worktrees/seo-index-policy`.
- The unrelated active WIP in the main checkout (`feature/blog-cover-fit-dedupe`) and `stash@{0}` (search-console) are NOT touched.

## Approved policy

| URL family | Behavior |
| --- | --- |
| `/catalog` (any params, incl. `?source=`) | `noindex, follow` — **preserved**, regression-asserted |
| `/bestsellers` `/trends` `/most-desired` clean URL (no query string) | indexable — preserved |
| same routes with **any** query string | `noindex, follow` (covers inert `?source=`, empty `q`, explicit `page=1`, etc.) |
| `/join/{code}` GET | `noindex, follow` + `Disallow: /join/` in `robots.txt` |
| `/p/{user_id}` | `noindex, follow` + removed from `sitemap.xml` |

Notes / decisions:

- For `/p/`, `noindex` + sitemap removal is authoritative; **no** `Disallow: /p/` (blocking crawl would hide the `noindex` and leave orphan URLs). Profiles stay reachable and shareable by direct link.
- For `/join/`, `Disallow` is intentional because the `code` is a secret: prevent crawling in the first place. The `noindex` is defense-in-depth.
- `/ideas/{slug}` is untouched (`always_indexable=True`); its `?page=N` remains indexable per item 1.
- `?category=` on legacy routes is *not* self-generated anymore (chips render only on `/catalog`) and is out of scope; noted for a future item.

## Constraints

- Keep Jinja2 + HTMX; no new dependencies; no Node/bundler. Keep the pinned requirements baseline.
- Routes stay thin; the noindex decision stays in `_catalog_context` (`openspec/config.yaml` design rules).
- Do not change the rendered content of any page — only indexability metadata, sitemap membership, and robots.txt.

## Files

- `main.py` — `robots.txt` (`Disallow: /join/`); `_catalog_context` noindex rule; `sitemap_xml` (drop profiles); three legacy routes pass the query-string signal.
- `templates/join.html` — `extra_head` `noindex, follow`.
- `templates/public_profile.html` — `extra_head` `noindex, follow`.
- `docs/superpowers/specs/2026-09-27-catalogo-navegable-design.md` — dated §18 amendment.
- `tests/test_seo_index_policy.py` — **new**, focused tests for all three policies.
- `odd/tasks/seo-index-policy.md` — this document.

## Task checklist and acceptance

### T1 — Invitation pages (`/join/{code}`)

- [x] RED → GREEN → refactor, one commit (`24928af`).
- Acceptance: Given `GET /join/ABC123`, Then status `200` and `<meta name="robots" content="noindex, follow">` in the head. Given `GET /robots.txt`, Then it contains `Disallow: /join/`.
- Evidence: RED focused 2 failed (no robots meta; no Disallow). GREEN focused 2 passed; full suite `--ignore=tests/test_e2e.py` 399 passed. Native review `medium`, 3 paths, 19 lines, lens `review-reliability` → **approved**, acknowledgement burned. Non-blocking advisory R3-001 (`main.py:89` SUGGESTION): the `Disallow` stops crawlers from reading the `noindex`; intentional defense-in-depth for a secret token, reconciled later via the design §18 note.

### T2 — Legacy catalog routes / `source` filter

- [x] RED → GREEN → refactor, one commit (`2af635f`).
- Acceptance:
  - Given `GET /bestsellers`, Then no `noindex` meta.
  - Given `GET /bestsellers?source=trends`, Then `noindex, follow` present.
  - Given `GET /bestsellers?q=&sort=relevance&source=bestsellers` (the form's own submit shape), Then `noindex, follow` present.
  - Same for `/trends` and `/most-desired` with `?source=…`.
  - Given `GET /catalog?source=trends`, Then `noindex, follow` present (regression).
  - Given `GET /ideas/{slug}` (valid, page 1), Then **no** `noindex` (regression; `/ideas` must not be caught by the new rule).
- Evidence: RED 4 failed (the `?source=` variants + form-submit shape) / 7 passed. GREEN focused 11 passed; full suite `--ignore=tests/test_e2e.py` 408 passed. Design §18 appended. Native review `medium`, 3 paths, 88 lines, lens `review-reliability` → **approved**, acknowledgement burned. Non-blocking advisory findings (logged, not applied to the frozen candidate): R3-coverage-follow (`tests/test_seo_index_policy.py:5-8` SUGGESTION — `_is_noindex` asserts only `noindex`, not `follow`); R3-param-order (`main.py:294` SUGGESTION — `has_query_params` placed before `editorial_context`; all callers use keywords).

### T3 — Public profiles (`/p/{user_id}`)

- [x] RED → GREEN → refactor, one commit (`5dc9cb4`).
- Acceptance:
  - Given a seeded user, When `GET /p/{id}`, Then status `200` and `noindex, follow` meta present.
  - Given `GET /sitemap.xml`, Then no `<loc>` contains `/p/`.
  - Regression: sitemap still contains home, `/amigo-invisible`, `/ideas/{slug}` and `/blog/{slug}`.
- Evidence: RED 2 failed (no robots meta on `/p/{id}`; `/p/{id}` present in sitemap) / 11 passed. GREEN focused 13 passed; full suite `--ignore=tests/test_e2e.py` 410 passed. Native review `medium`, 3 paths, 36 lines, lens `review-reliability` → **approved**, acknowledgement burned. Non-blocking advisory R3-001 (`tests/test_seo_index_policy.py:78-86` SUGGESTION): the sitemap test hardcodes the default `DOMAIN_URL` home `<loc>`, so it is environment-dependent.

Required existing test changes (explicit, not hidden): none expected. `test_seo_landings.py::test_organizer_sitemap_is_unique_and_robots_allow_public_landings` must keep passing (it asserts home/amigo-invisible counts and no `Disallow: /amigo-invisible`).

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`). Runner: `/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest -q tests/test_seo_index_policy.py
/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

## Review workload and delivery

| Work unit | Forecast authored additions + deletions |
| --- | ---: |
| T1 join + robots + tests | ~25-40 |
| T2 legacy/source + tests + design §18 | ~50-90 |
| T3 profiles + sitemap + tests | ~30-60 |
| Total | ~105-190 |

- **Delivery: `single-pr`** (user approved one PR with T1+T2+T3). Forecast is well under the 400-line advisory.
- RDD is on (global): each work-unit commit is a review candidate; native assessment + the lens selected by the native plan, with per-candidate consent.

## Rollback

Revert the T1/T2/T3 commits; the changes are metadata-only and additive except the sitemap profile loop removal (restore the loop to re-submit profiles). No production data, credentials, or content changes.

## Progress

- [x] Mapped scope (read-only) against `main`; corrected the `source` premise (not a bound param on legacy routes).
- [x] Product decision for profiles recorded: `noindex, follow` + out of sitemap.
- [x] Worktree `…-worktrees/seo-index-policy` created from `main` (`edf2ab5`); main checkout WIP untouched.
- [x] T1 (`24928af`) — approved/burned.
- [x] T2 (`2af635f`) — approved/burned.
- [x] T3 (`5dc9cb4`) — approved/burned.
- [x] ODD doc committed; branch pushed; PR opened to `main` (merge is user-owned).

## Follow-ups (non-blocking advisory findings, acknowledged)

- R3-coverage-follow (`tests/test_seo_index_policy.py:5-8`): tighten `_is_noindex` / the T2 assertions to assert `follow` explicitly, matching §18.
- R3-param-order (`main.py:294`): consider moving `has_query_params` after `editorial_context` (or making the new params keyword-only) to remove positional-caller risk.
- R3-001 (`tests/test_seo_index_policy.py:78-86`): derive the sitemap expected domain from the same fallback, or set/clear `DOMAIN_URL` in the test, to remove environment dependence.
