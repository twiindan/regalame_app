# Christmas gift guide (roadmap item 5)

Roadmap item 5 of the persisted roadmap `seo/next-improvements-roadmap` (Engram #932):
"one or two human-reviewed Christmas guides", framed as the first editorial pilot.
This is the only ODD planning artifact for this feature.

## Objective, problem, and why

The blog (`blog_config.BLOG_POSTS` -> `/blog/{slug}`) is the app's curated-guide surface,
but it had no Christmas-intent guide; the only Christmas-adjacent surfaces were
`/amigo-invisible` and the `regalos-amigo-invisible-10-euros` post. A seasonal guide
targets gift-giver demand into the app's acquisition funnel.

Product decisions made by the user (2026-10-08):

- **Form:** curated blog post (existing guide system). The user reviews copy and the
  product selection before delivery.
- **Topic:** Christmas gift guide. Originally "the most-wanted products across the whole
  catalog", later corrected (see below) to a **hand-curated ASIN list**.

## Why the automatic "most-wanted" approach was dropped

The guide ordering is by `productlist.rank`, but that is **not a popularity rank**: the
scraper walks the Amazon sidebar category by category (`scraper.py:114`) and stores 50
products per category, so the JSON inputs and `rank` are grouped by category. All three
`amazon_*_total.json` start with "Alimentación y bebidas". Verified read-only on
`database.db`: the top 12 and **all 85** products with `min(rank) <= 30` are that single
category. Any filter-less or price-only guide therefore renders one category — useless as
a gift guide. This is systemic (production imports the same files).

Consequence: the guide uses an explicit, human-reviewed ASIN list instead of a catalog
filter. The user approved a 27-product selection spanning 12 categories from a
60-candidate board, with all 27 verified present/active/with image in `database.db`.

## Authorized scope and boundary

- Authorized: local implementation, strict TDD, tests, minimal config/services/catalog
  edits, work-unit commits on `feature/christmas-guide` (base `main` @ `a9ac899`), ODD doc.
- Not authorized: push, PR, merge (user-owned; performed at close after human review).
- No new dependencies; keep Jinja2 + HTMX; no Node/bundler.
- No change to behavior of existing posts; no changes to `/ideas`, `/catalog`, sitemap
  policy for other surfaces, or profile/indexability rules.
- Untracked `sample.json` / `sample.curacion-worktree.json` are not touched.

## Task checklist and acceptance

### WU-1 — Optional `criteria["limit"]` cap — `d32721c`

- [x] RED -> GREEN -> refactor.
- Acceptance: a positive-int `limit` caps collected products; omitted/invalid `limit`
  keeps the previous behavior (all matches). Combines with curated items.

### WU-2 — Hand-curated `criteria["items"]` — `f803f61`

- [x] RED -> GREEN -> refactor.
- `catalog.products_by_asins(session, asins)` resolves an explicit ASIN list, preserving
  authored order, collapsing duplicates and dropping unknown, inactive or editorially
  hidden products. `services.get_blog_post_detail` uses it when `criteria["items"]` is a
  non-empty list; the `limit`, if any, applies after resolution.

### WU-3 — Christmas guide entry — `7da2cf8`

- [x] RED -> GREEN -> refactor + intended sitemap golden regeneration.
- `BLOG_POSTS` gains `regalos-navidad-mas-deseados` with the approved 27-ASIN
  `criteria["items"]`, `hero_image: None`.
- Acceptance: `GET /blog/regalos-navidad-mas-deseados` is `200`, single H1 with the post
  title, opt-in self-canonical; the curated ASIN renders; the URL is in `sitemap.xml`;
  the organizer aside stays scoped to `regalos-amigo-invisible-10-euros`.

## Constraints and conventions

- Business logic stays in `services.py`/`catalog.py`; routes stay thin.
- UI copy: neutral Spanish. Technical docs: English.
- No AI attribution in commits; Conventional Commits only.
- Golden baselines regenerated **only** for the intended sitemap URL.

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`: `strict_tdd: true`, `apply.tdd: true`).
Runner: `/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest`.

Observed results:

- WU-1 focused RED `1 failed, 5 passed` -> GREEN focused `6 passed`; full suite `500 passed`.
- WU-2 focused RED `4 failed, 6 passed` -> GREEN focused `10 passed`; full suite `504 passed`.
- WU-3 focused RED `4 failed, 10 passed` -> GREEN focused `14 passed`; full suite `510 passed`.
- Sitemap golden diff is exactly the new `<url>` block (6 lines); every other surface
  byte-for-byte unchanged.

## Review workload and delivery

| Work unit | Authored additions + deletions |
| --- | ---: |
| WU-1 limit + tests | ~34 |
| WU-2 curated items + tests | ~113 |
| WU-3 guide + tests + golden | ~95 |
| ODD doc | ~110 |

- **Delivery: `single-pr`**; total is under the 400-line advisory, no `size:exception`.
- RDD is on (global). Known machine issue: the native reviewer sub-agent returns empty
  output (`opencode_task_output_empty`); reported to the user if it recurs.

## Rollback

Revert the WU-1/WU-2/WU-3 commits: additive changes (one config entry, one ASIN resolver,
an optional cap). No production data, credentials, migrations, or content changes.

## Progress

- [x] Exploration: guide surfaces, catalog counts, golden surfaces, rank semantics mapped.
- [x] Product decisions: form = curated blog post; selection = 27 approved ASINs.
- [x] WU-1 (`d32721c`), WU-2 (`f803f61`), WU-3 (`7da2cf8`).
- [ ] Push / PR / merge — user-owned, pending explicit go-ahead.
