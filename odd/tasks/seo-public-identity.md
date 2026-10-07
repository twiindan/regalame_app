# SEO public identity and affiliate quick wins (roadmap item 3)

ODD planning artifact for this feature. Single feature document (no separate plan file).
Roadmap source: `seo/next-improvements-roadmap` (Engram obs #932), item 3.

## Objective, problem, and why

Roadmap item 3 bundles four low-risk, high-value SEO/monetization corrections. Verified
defects on `https://regalame.app` (read-only exploration, 2026-10-07):

1. **Social image is a hard 404.** `static/` contained only `.gitkeep`, yet
   `templates/base.html:36,43` point `og:image` and `twitter:image` at
   `https://regalame.app/static/og-image-default.jpg`, which does not exist. Every share
   preview currently renders without an image.
2. **The public origin is scattered and contradictory.** `base.html:33,40` hardcode
   `https://regalame.app/` for `og:url`/`twitter:url` (ignoring `DOMAIN_URL`), while the
   sitemap, `robots.txt` and landing canonicals read `os.getenv("DOMAIN_URL", ...)` in four
   places in `main.py` (82, 94, 151, 158). The existing test parametrizes `DOMAIN_URL` with
   `https://landing.example/`, so identity tags disagree under any non-default origin.
3. **Indexable pages carry no self identity.** Only `/` and `/amigo-invisible` set a
   canonical. `/blog`, `/blog/{slug}`, `/bestsellers`, `/trends`, `/most-desired` have no
   canonical and fall back to a homepage `og:url`. `/ideas/{slug}` has a relative canonical
   but a homepage `og:url`. `/catalog` is `force_noindex` and MUST stay noindex.
4. **Affiliate links are under-declared.** Affiliate/store anchors carry no `rel`; the
   `generate_amazon_link` default tag is the placeholder `tu_tag_defecto-21` and an unset
   `AMAZON_TAG` is silently accepted. Verified: `wish.url` is ALREADY generated through
   `generate_amazon_link` at creation (`main.py:856,867,869`), so wish links are not
   untagged. `inspiration.html` is dead code (no route renders it).

## Authorized scope and current boundary

- Authorized: local implementation in worktree `seo-public-identity`, strict TDD, tests, one
  work-unit commit per task, regenerate the editorial golden baselines.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Base: `main` at `dd02c4a`. Branch `feature/seo-public-identity` created before the first write.
- Out of scope: public-profile JSON-LD removal (profile is already noindex), performance
  (roadmap item 6), Search Console baseline (roadmap item 4), removing the affiliate
  placeholder in code (only a startup warning is added).

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `static/og-image-default.jpg` | a real 1200x630 branded asset exists and is committed |
| `og:image` / `twitter:image` | point at the real asset, with `og:image:width/height/alt` and `twitter:image:alt` |
| public origin | one `public_origin()` helper is the single source of truth; sitemap, robots and every identity tag use it |
| indexable pages | `/`, `/amigo-invisible`, `/ideas/{slug}`, `/blog`, `/blog/{slug}`, `/bestsellers`, `/trends`, `/most-desired` emit a self canonical and a self `og:url`/`twitter:url` |
| blog post | `og:image` is the post hero image when present, else the default asset |
| noindex pages | `/catalog`, `/join/{code}`, `/p/{user_id}` keep `noindex, follow` and do not gain a canonical |
| affiliate/store anchors | carry `rel="sponsored nofollow noopener"` (blog, catalog results, dashboard, wish item, my_draw) |
| `AMAZON_TAG` unset | startup warns once; link generation keeps working (no crash, no test breakage) |
| `inspiration.html` | left unchanged (dead code; flagged as follow-up, not touched) |

## Constraints

- Business logic stays in `services.py`; routes stay thin; templates consume context only.
- No new dependencies; Jinja2 + HTMX + TailwindCSS only.
- `DOMAIN_URL` default stays `https://regalame.app`, trailing slash stripped.
- `test_category_retains_its_existing_relative_canonical` MUST stay green (relative `/ideas/...`).
- Landings keep ignoring query strings and emit the clean configured absolute identity.

## Files

- `main.py` — `public_origin()` + `social_url()` Jinja globals; `canonical_url` unified context;
  thin routes set identity; sitemap/robots/landings use the helper.
- `templates/base.html` — canonical from `canonical_url`; `og:url`/`twitter:url` via
  `social_url(canonical_url)`; real image + size/alt tags; `og:image` override support.
- `templates/category_seo.html` — drop the duplicate canonical (base now owns it); keep prev/next.
- `templates/blog_post.html` — `og:image` = hero image; affiliate `rel`.
- `templates/blog_index.html` — index identity is route-provided; verify no local canonical.
- `templates/partials/catalog_results.html`, `templates/dashboard.html`, `templates/my_draw.html`,
  `templates/partials/wish_item.html` — affiliate/store `rel="sponsored nofollow noopener"`.
- `services.py` — `AMAZON_TAG` startup warning; keep link generation behavior.
- NOTE: `wish.url` is already affiliate-generated; do NOT re-wrap it. `inspiration.html` is dead code.
- `static/og-image-default.jpg` — new real asset.
- `tests/test_seo_landings.py` — update `/blog` expectation; add identity + image assertions.
- `tests/test_editorial_filtering.py` baselines — regenerate all 9 golden snapshots.

## Task checklist and acceptance

- [ ] **T1 — Real social image**: commit `static/og-image-default.jpg` and emit it with
      `og:image:width=1200`, `og:image:height=630`, `og:image:alt`, `twitter:image:alt`.
- [ ] **T2 — Validated public origin**: `public_origin()` used by sitemap, robots, landings and
      every identity tag; no hardcoded origin left in `base.html`.
- [ ] **T3 — Per-page identity**: self canonical + self `og:url`/`twitter:url` on the indexable
      pages; blog post hero as `og:image`; noindex pages unchanged; baselines regenerated.
- [ ] **T4 — Affiliate/sponsored**: `rel="sponsored nofollow noopener"` on affiliate/store anchors;
      `AMAZON_TAG` unset logs one warning.

Acceptance (Given/When/Then):

- Given `DOMAIN_URL=https://landing.example/`, When `/blog` is requested, Then canonical is
  `/blog` and `og:url`/`twitter:url` are `https://landing.example/blog`.
- Given `GET /blog/{slug}`, When the post has a hero image, Then `og:image` equals that image.
- Given `GET /catalog` or `/trends?q=x`, Then no canonical is emitted and robots contains noindex.
- Given `GET /ideas/alimentacion-y-bebidas`, Then the canonical is exactly the relative path.
- Given any affiliate anchor, Then it has `rel="sponsored nofollow noopener"`.
- Given `AMAZON_TAG` unset, When a wish is created, Then the stored/generated link still contains `tag=`.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_seo_landings.py tests/test_seo_index_policy.py tests/test_services.py tests/test_catalog_routes.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

Baselines are regenerated once with `venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines`, then a normal run must match byte-for-byte.

## Progress log

- 2026-10-07: read-only exploration (Engram obs #978); worktree `feature/seo-public-identity`
  created off `main@dd02c4a`; real `static/og-image-default.jpg` (1200x630 JPEG, 46 KB) rendered
  with Playwright + Chromium and placed in the worktree.
