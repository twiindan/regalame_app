# SEO Improvements

## Objective
Raise the technical and on-page SEO of the public surfaces (home, `/amigo-invisible`,
`/ideas/{slug}`, `/blog`, `/blog/{slug}`, catalog landing pages) without changing product
behavior: correct structured data per page type, breadcrumbs, a complete sitemap, and
self-hosted HTMX.

## Problem
The SEO base is good (per-page title/description, canonical, OG/Twitter, robots.txt,
dynamic sitemap, noindex policy, pSEO `/ideas/{slug}`). Gaps found in the audit:

1. `templates/base.html` emits a `SoftwareApplication` JSON-LD on **every** page; blog
   posts and category pages carry no page-type schema (`BlogPosting`, `CollectionPage`,
   `ItemList`, `BreadcrumbList`), and the home lacks `WebSite`/`Organization`/`SearchAction`.
2. No breadcrumbs anywhere (neither visible nor `BreadcrumbList`).
3. `/sitemap.xml` omits `/blog`, `/bestsellers`, `/trends`, `/most-desired` and emits no
   `<lastmod>`.
4. HTMX is loaded from `https://unpkg.com` in `<head>` (render-blocking, third-party,
   no SRI).
5. `/ideas/{slug}` pSEO pages are thin (single templated paragraph).

## Why
These are the highest-impact, lowest-risk SEO wins: rich-result eligibility, crawl
efficiency, Core Web Vitals (LCP/TBT), and pSEO quality.

## Scope
In scope: `templates/base.html`, `templates/index.html`, `templates/blog_post.html`,
`templates/category_seo.html`, `templates/catalog.html`, `templates/public_profile.html`,
`templates/partials/*`, a new breadcrumbs partial/macro, `main.py` (SEO routes only),
`static/js/htmx.min.js` (vendored), `tools/` (vendor script), `tests/` (SEO tests +
baselines), `odd/`.

Out of scope: auth, groups, wishes, chat, scraper, curation, editorial filtering behavior,
delivery to production (push/PR/merge are the user's decisions).

## Constraints
- The repo encodes SEO intent in tests: `tests/test_seo_landings.py` pins canonical
  (home = absolute configured origin; others = relative), og:url fallback to home on
  noindex pages, og:image dimensions, no `FAQPage` on `/`, `/amigo-invisible`, `/catalog`,
  `/blog`. Do **not** break these silently; extend tests only with intent.
- `tests/test_editorial_filtering.py` golden baselines (`tests/baselines/editorial_off_*.html`)
  must be regenerated with `--editorial-update-baselines` after any rendered-HTML change.
- `tests/test_assets.py` guards asset delivery (no render-blocking third-party fonts/Tailwind/
  Phosphor, JS-toggled classes present in generated CSS). New static Tailwind classes require
  regenerating `static/css/tailwind.css` via `tools/build_tailwind.sh` (v4.3.3 binary is
  cached in `tools/.bin/`, offline OK). Prefer reusing existing utility classes.
- `sitemap.xml` output does NOT pass through `base.html` (built in `main.py`), so a base
  template change does not affect the sitemap baseline and vice versa.
- Functional artifacts (code, comments, tests, commits) in English.

## Tasks

- [ ] **T1 — sitemap + robots hardening** (`main.py`)
  - Add `/blog`, `/bestsellers`, `/trends`, `/most-desired` to `/sitemap.xml`; add
    `<lastmod>` where a real date exists (sitemap itself has no per-item dates → only add
    `<lastmod>` if derivable, otherwise document why not). Keep `media_type="application/xml"`.
  - `robots.txt`: keep `Allow: /` and current disallows; do not disallow public landings.
  - Route: direct inline (small, `main.py`-only + sitemap baseline). Files: `main.py`,
    `tests/test_seo_index_policy.py`, `tests/baselines/editorial_off_sitemap.html`.
  - Checks: `/sitemap.xml` well-formed XML, includes the new locs exactly once;
    `test_seo_index_policy.py` + `test_seo_landings.py::test_organizer_sitemap_*`;
    regenerate sitemap baseline.

- [ ] **T2 — self-host HTMX** (`base.html` + `static/js/`)
  - Vendor htmx 1.9.10 into `static/js/htmx.min.js`; reference it with `defer`; drop the
    unpkg URL. Add a `tools/` script only if a reproducible vendor step is warranted.
  - Route: direct inline. Files: `templates/base.html`, `static/js/htmx.min.js`,
    `tests/test_assets.py`, all `tests/baselines/editorial_off_*.html` except `sitemap`.
  - Checks: no `unpkg.com` in rendered HTML; HTMX still functions (grep for
    `hx-` attributes and that the script tag is local); `test_assets.py`; regenerate baselines.

- [ ] **T3 — rich results: per-page structured data + breadcrumbs**
  (`base.html`, `index.html`, `blog_post.html`, `category_seo.html`, `public_profile.html`)
  - Make `base.html` structured data overridable/extendable: keep the existing
    `SoftwareApplication` default (tests depend on it on `/`, `/amigo-invisible`, `/catalog`,
    `/blog`) and add page schemas additively via `extra_head`:
    home → `WebSite` + `SearchAction` + `Organization`; blog post → `BlogPosting`
    (`datePublished`/`dateModified` if available, `author`, `publisher`, `image`) and
    `og:type=article` + `article:published_time`; category → `CollectionPage` + `ItemList`.
  - Add visible breadcrumbs + `BreadcrumbList` on `/blog/{slug}` and `/ideas/{slug}` via a
    new macro/partial and a `{% block %}` hook in `base.html`.
  - Route: delegated writer (multi-file + tests). Files as above + `tests/test_seo_landings.py`
    (+ new test file if clearer) + affected baselines.
  - Checks: valid JSON-LD (`json.loads` parses each block), correct `@type` per page,
    canonical/og policy tests still green, breadcrumbs present, baselines regenerated.

- [ ] **T4 — `/ideas/{slug}` content depth**
  (`category_seo.html` + content source)
  - Add a category-aware "how to choose" section, a price-range note, an FAQ (with
    `FAQPage` JSON-LD — allowed on `/ideas`, which the metadata test does not cover), and
    internal links to relevant blog posts. Copy must stay factual (no invented claims).
  - Route: delegated writer. Files: `templates/category_seo.html`, a content module or
    `blog_config`/`catalog` helper, `main.py` (pass context), tests, ideas baseline.
  - Checks: `/ideas/{slug}` renders the new sections; JSON-LD parses; 404 policy unchanged;
    baselines regenerated.

## Acceptance criteria
- `/sitemap.xml` lists home, `/amigo-invisible`, every visible `/ideas/{slug}`, every blog
  post, and the indexable catalog landings, exactly once each; valid XML.
- No third-party render-blocking script remains in `<head>`.
- Each page type carries appropriate, parseable JSON-LD; no `FAQPage` on the four pages the
  metadata test covers.
- Breadcrumbs render and validate on blog posts and category landings.
- The full suite passes; any regenerated baseline diff is intentional.

## Verification
- `venv/bin/python -m pytest -q` (full suite) from the repo root.
- Focused: `venv/bin/python -m pytest -q tests/test_seo_landings.py tests/test_seo_index_policy.py tests/test_assets.py`.
- Baseline regen: `venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines`.

## Delivery strategy
`ask-on-risk` (default). Forecast authored lines (templates + main.py + tests, generated
baselines excluded): ~450–600 → likely crosses the ~400 budget, so expect chained PRs
(`stacked-to-main`) unless the user prefers a single PR per branch.

## Routes
- T1: direct inline (main.py-only).
- T2: direct inline (base.html one region + vendored asset).
- T3: delegated writer.
- T4: delegated writer.

## Progress
- [x] Audit + branch topology decided (4 branches; wave 1 parallel, wave 2 sequential).
- [x] T1 — sitemap + robots hardening (`feat/seo-sitemap-robots`).
- [x] T2 — self-host HTMX (`feat/seo-htmx-local`).
- [x] T3 — structured data + breadcrumbs (`feat/seo-rich-results`).
- [x] T4 — `/ideas/{slug}` content depth (`feat/seo-category-content`).
- [x] Integrated verification on `integration/seo-check`.

## Evidence
- Audit findings recorded in Engram (`seo/audit-regalame`).
- Branch/commit identities recorded below.
- Worktrees live under `/Users/toni.robres/Pycharmprojects/regalame_gemini3-worktrees/`.
- Focused suites per branch green; integrated full suite = **556 passed, 8 known
  pre-existing environmental failures** (2 Playwright/chromium e2e; 6 scraper/refresh
  asyncio-ordering). The same 8 fail on a clean `main`, proven before integration.

| Task | Branch | Commit |
|------|--------|--------|
| T1 | `feat/seo-sitemap-robots` | `8113af5` |
| T2 | `feat/seo-htmx-local` | `62a213f` |
| T3 | `feat/seo-rich-results` (stacked on T2) | `7fdf08c` |
| T4 | `feat/seo-category-content` (stacked on T3) | `5eb3ef0` |
| — | `integration/seo-check` (all 4 merged) | `15d25c8` |

## Native review (RDD)
RDD is `on` (global). `gentle-ai review assess --base-ref c0d73f0 --committed-only`
returned `review_due: true`, `high_risk`, 21 files / 737 lines, with reason codes
`dangerous_sink` (a vendored minified JS asset), `executable_mode` / `process_boundary`
/ `shell_source` (a vendored shell script). The granted START failed with
`candidate_context_unavailable` ("unsupported negotiated START risk reason
dangerous_sink") yet still minted a `reviewing` lineage — the same causal class as
upstream `Gentleman-Programming/gentle-ai#5195`.

- Reported as one occurrence comment (no labels changed):
  https://github.com/Gentleman-Programming/gentle-ai/issues/5195#issuecomment-6077521257
- Per the defect handoff, the captured v3 decline invocation ran exactly once and
  validated (`action: declined`, `consent: declined_this_candidate`, target identity
  match); the wedged lineage then went terminal `invalidated` and STATUS returned to
  `fresh_target_ready`.
- No delivery authority burned; no repository mutation beyond the local authority store.

## Next step
The candidate is released and unreviewed. Push / PR / merge are the user's decision
under ordinary repository policy.

## Delivery (PR slices)
All five branches are pushed and their PRs are open; CI (`Clean install + test suite`)
is green on each.

| PR | Head → Base | Holds |
|----|-------------|-------|
| #72 | `docs/seo-improvements` → `main` | This tracker. |
| #73 | `feat/seo-sitemap-robots` → `main` | Commit `8113af5` (sitemap + robots). |
| #74 | `feat/seo-htmx-local` → `main` | Commit `62a213f` (self-host htmx). |
| #75 | `feat/seo-rich-results` → `feat/seo-htmx-local` | Commit `7fdf08c` (structured data + breadcrumbs). |
| #76 | `feat/seo-category-content` → `feat/seo-rich-results` | Commit `5eb3ef0` (category content). |

Merge order: #74 → #75 → #76 (the T2→T3→T4 chain); #72 and #73 are independent.
