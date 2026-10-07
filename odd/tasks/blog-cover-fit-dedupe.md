# Blog cover images: fit instead of crop, and distinct images per card

ODD planning artifact for this feature. Single feature document (no separate plan file).

## Objective, problem, and why

On `https://regalame.app/blog` the cover images of the article cards have two defects:

1. **Cropped covers.** Each card renders `object-cover` inside a fixed `h-48` box
   (`templates/blog_index.html:27`), so tall product photos are cut off. The user asked for the
   image to *fit* and look right.
2. **Duplicated covers.** Covers are resolved independently per post
   (`services.get_blog_posts_with_covers`), each taking the first visible product that matches its
   criteria. Overlapping criteria (the two price buckets: `<10€` and `<20€`) resolve to the **same
   first product**, so the first two cards show the identical image (verified live:
   `...I/61q0ADUxliL...` in both cards). The user asked that when the image is already used, the
   card advances to another product's image.

## Authorized scope and current boundary

- Authorized: local implementation, strict TDD, tests, one work-unit commit on
  `feature/blog-cover-fit-dedupe`.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Base: `main` at `edf2ab5`. Branch created before the first write.
- Out of scope: the `/blog/{slug}` article banner (its `object-cover` + exact class is pinned by an
  existing test and a golden baseline; it is a wide banner, not a card). Sitemap, `BLOG_POSTS`
  content, and hand-curated hero URLs are also out of scope.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `/blog` index card | cover image fits (`object-contain`) inside a neutral/white frame instead of being cropped |
| `/blog` index covers | a card never reuses an image already used by an earlier card; it advances to the next visible product with an unused image |
| `/blog` index covers (exhausted) | if no unused image exists, fall back to the first visible product image; if none, keep the gradient fallback |
| hidden products | never used as a cover (existing `search_products` editorial predicate) |
| module-level `BLOG_POSTS` | never mutated; enriched copies only |

## Constraints

- Business logic stays in `services.py`; the route stays thin (`openspec/config.yaml` design rules).
- No new dependencies; Jinja2 + HTMX + TailwindCSS only.
- Covers are resolved through `search_products` so the editorial predicate applies.
- Match the established product-image pattern used elsewhere (`bg-white` + `object-contain`).

## Files

- `services.py` — `get_blog_posts_with_covers(session)` tracks already-used images and picks the
  first unused candidate.
- `templates/blog_index.html` — card cover uses `object-contain` inside a neutral frame.
- `tests/test_catalog.py` — dedupe resolution test(s).
- `tests/test_editorial_filtering.py` — index rendering test for the fit class.

## Task checklist and acceptance

- [x] **T1 — Fit covers**: `/blog` card cover renders `object-contain` (no crop), not `object-cover`.
- [x] **T2 — Distinct covers**: posts with overlapping criteria get different cover images.

Acceptance (Given/When/Then):

- Given `GET /blog`, When a card has a hero image, Then its `<img>` fits (`object-contain`) and the
  index contains no `object-cover`.
- Given two posts whose criteria overlap and two visible products, When covers are resolved, Then
  the two cards have different `hero_image` URLs (first product for the first post, the next unused
  product for the second).
- Given every candidate image is already used, When covers are resolved, Then the post falls back
  to the first visible product image without raising.
- Given an editorial-hidden product, When covers are resolved, Then the cover is not derived from it.
- Given `BLOG_POSTS`, When covers are resolved, Then the module-level entries still have
  `hero_image is None`.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_catalog.py tests/test_editorial_filtering.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

## Progress log

- Created the branch and this document before the first source write.
- T1 committed as `07f65ad` (`feat(blog): fit cover images on blog index cards`). Native assess:
  `medium` (executable_change in `templates/blog_index.html`) → deferred to the slice boundary.
- Foreground checks: `tests/test_catalog.py tests/test_editorial_filtering.py` → 88 passed;
  full suite (`--ignore=tests/test_e2e.py`) → 399 passed. Real local catalog: 11 resolved covers,
  0 duplicates; first two cards now resolve to different images.
- Native review `review-e7ec250290c37411` (lens `review-reliability`): **APPROVED**, receipt burned.
- Follow-up (this commit): added `test_get_blog_posts_with_covers_falls_back_when_no_unused_image`
  to close advisory finding **R3-1** (the exhausted-candidates fallback had no test). Remaining
  advisory, not addressed: **R3-2** (dedupe scans one page, `per_page=MAX_PER_PAGE`; theoretical at
  11 posts) and **R3-3** (curated `hero_image` not deduped against auto covers; pre-existing).
