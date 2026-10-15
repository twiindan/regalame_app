# Christmas SEO refresh: dynamic footer year, guide CTAs, evergreen tech slug

ODD planning artifact for the `seo-christmas-refresh` work unit. Single
feature document.

## Objective, problem, and why

December traffic season is close. The technical SEO layer (canonicals,
FAQPage, sitemap lastmod) is already deployed; this work unit is a small,
safe content/seasonality pass on top of `main`. Four fixes and one
review-only check:

- The footer copyright year is hardcoded to 2025 (`templates/base.html:187`)
  and goes stale every January.
- The home "Listas para Navidad y amigo invisible" section and
  `/amigo-invisible` do not link to the Christmas gift guide post
  `/blog/regalos-navidad-mas-deseados`, missing the seasonal internal
  linking opportunity.
- The technology post slug carries the year
  (`top-tendencias-tecnologia-2025`), which goes stale every season; the
  goal is a cumulative, evergreen URL with a 301 from the old slug.

## Authorized scope and current boundary

- Authorized: branch `feat/seo-christmas-refresh` from `main` (f762c51,
  already checked out and clean), local implementation, exactly one
  work-unit commit `feat(seo): ...`. No push, no PR, no deploy.
- Content policy: no invented claims, prices, or ratings. All site text in
  natural Spain-Spanish.
- Out of scope: `sitemap.py`, canonicals, schema, existing routes (except
  the T4 301), new posts, deployments/Railway config, the Christmas post's
  ASINs/products.
- Baseline policy: golden baselines regenerate only where content actually
  changes, using the repo standard `--editorial-update-baselines` flag
  (`tests/conftest.py:26`); never `datetime.now()` as lastmod; unexpected
  baseline diffs are reverted and reported.
- Known deviation from the original brief: not only the sitemap baseline
  changed. The footer lives in `base.html`, inherited by every page, so 8
  `editorial_off_*.html` baselines gained the dynamic year,
  `editorial_off_home.html` also gained the new CTA, and the sitemap
  baseline changed only the tech post `<loc>` — its `lastmod` is untouched
  (content did not change; no `datetime.now()` was introduced).

## Approved behavior

| Surface | Behavior |
| --- | --- |
| Footer (`base.html`) | copyright year rendered dynamically (system year; 2026 today); no hardcoded year remains |
| Home (`index.html`) | "Listas para Navidad" section gains a CTA to `/blog/regalos-navidad-mas-deseados` ("Descubre los regalos más deseados para Navidad"), same link style as existing links (`text-pink-300 hover:text-white underline`) |
| `/amigo-invisible` | second link under the 10€ post link, same pattern, to the Christmas post |
| Blog tech post | slug `top-tendencias-tecnologia-2025` → `mejores-gadgets-tecnologia` (title/description unchanged, already year-free); old slug answers 301 permanent → new slug; new slug answers 200 with the correct title |
| Internal references | references to the old slug (blog_config related_posts, the listed test pins, any other hardcoded reference found by grep) point to the new slug; the 301 keeps external links working |
| Christmas post | review-only: FAQ still valid ("cuándo conviene hacer las compras", "amigo invisible"); no ASIN or product changes expected |

## Files

- `templates/base.html` — dynamic footer year (mechanism chosen to fit how
  context reaches templates; expected: Jinja global near the existing
  pattern used by `social_url`).
- `templates/index.html` — Christmas guide CTA.
- `templates/amigo_invisible.html` — second guide link.
- `blog_config.py` — evergreen slug (+ related_posts references if any).
- `main.py` — 301 permanent redirect old slug → new slug (+ year plumbing
  if that is the chosen mechanism).
- `tests/test_seo_landings.py`, `tests/test_catalog.py` — updated pins
  (related_posts expectation, get_blog_post_detail criteria call).
- `tests/test_christmas_refresh.py` — new suite: footer year, home CTA,
  amigo-invisible both hrefs, evergreen slug 200 / legacy slug 301.
- `tests/baselines/editorial_off_*.html` — regenerated via the standard
  `--editorial-update-baselines` flag (all 9, shared footer).
- `seo_content.py` needed no change: `related_posts` resolves slugs
  dynamically from `BLOG_POSTS`.

## Task checklist and acceptance

- [x] **T1** — dynamic footer year; home renders `© 2026` and not `© 2025`.
- [x] **T2** — home CTA to the Christmas guide post; home contains
      `href="/blog/regalos-navidad-mas-deseados"`.
- [x] **T3** — `/amigo-invisible` contains both hrefs (10€ post + Christmas
      post).
- [x] **T4** — evergreen slug: new slug 200 with correct title, old slug
      301 permanent; pins updated; all 9 baselines regenerated (shared
      footer).
- [x] **T5** — review-only: Christmas post FAQ valid; no code change
      needed.
- [x] Full suite green: `./venv/bin/python -m pytest tests/ -q
      --ignore=tests/test_e2e.py` → 715 passed.

## Evidence

- RED observed: `tests/test_christmas_refresh.py` — 5 failed against the
  pre-change code (stale footer year, missing CTAs, evergreen slug 404,
  legacy slug 404 instead of 301).
- GREEN: `tests/test_christmas_refresh.py` — 5 passed.
- T1 mechanism: `current_year()` Jinja global (render-time evaluation, so
  long-lived processes never serve a stale year), registered next to the
  existing `social_url` / `category_meta` globals in `main.py`; template
  renders `&copy; {{ current_year() }}`.
- Pins: `tests/test_seo_landings.py` related_posts expectation and
  `tests/test_catalog.py` criteria call moved to
  `mejores-gadgets-tecnologia`; repo-wide grep found no other hardcoded
  old-slug references outside baselines.
- Baselines regenerated with `--editorial-update-baselines`: diff audited
  line by line — 8 footers `2025→2026`, home CTA addition, sitemap `<loc>`
  swap only. No lastmod changed; stable on a second suite run without the
  flag.
- T5 verdict: the Christmas post FAQ already covers "¿Cuándo conviene hacer
  las compras de Navidad?" and "¿Sirve esta selección para un amigo
  invisible?"; title, criteria and ASINs untouched. No change needed.
- Delegation deviation: the gentle-ai worker/verify subagent runtime was
  unavailable (capacity quarantined, 0 turns on two attempts), so
  implementation and the full-suite run executed inline in the parent
  session, test-first.
- Full suite: `./venv/bin/python -m pytest tests/ -q --ignore=tests/test_e2e.py`
  → 715 passed.
- Commit: `feat(seo): christmas refresh with dynamic year, guide CTAs,
  evergreen slug` on branch `feat/seo-christmas-refresh` (no push, no PR).
- RDD review preflight BLOCKED (harness-side): two `gentle_review` START
  attempts (fresh idempotency keys, stable inspect between them) both
  failed before the native operation with `candidate-view-invalid`,
  `lineage_created: false`, no mutation; repair assessment unsupported
  with zero lineages. The candidate stays unreviewed; retrying the review
  (`gentle-ai review start` or a fresh inspect) is a pending human
  decision. No review authority was invented or claimed.
