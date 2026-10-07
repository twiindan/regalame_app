# Blog cover images: resolve and render a cover for every curated article

ODD planning artifact for this feature. Single feature document (no separate plan file).

## Objective, problem, and why

`/blog` lists 11 curated articles. Every `BLOG_POSTS` entry has `hero_image: None`
(`blog_config.py`), and the `/blog` route serves `BLOG_POSTS` unmodified, so every index card
falls back to the gradient + gift-icon placeholder — no cover image is ever shown. The article
page (`/blog/{slug}`) already derives `hero_image` in `services.get_blog_post_detail` (first
visible product), but `templates/blog_post.html` never renders it, so the article has no cover
either.

The user chose on 2026-10-07: **cover = the first visible product image of each post's criteria**
(automatic, always in sync with the catalog). Applied to both the `/blog` index cards and the
article header.

## Authorized scope and current boundary

- Authorized: local implementation, strict TDD, tests, regeneration of the blog-detail golden
  baseline, one work-unit commit on `feature/blog-cover-images`.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Base: `main` at `27dfdfd`. Branch `feature/blog-cover-images` created before the first write.
- Out of scope: hand-curated hero URLs, per-category illustrations, sitemap changes.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `/blog` index card | cover = first visible product image for the post's criteria; gradient fallback when none |
| `/blog/{slug}` header | render `post.hero_image` as a banner; render nothing when none |
| `/sitemap.xml` | unchanged — must NOT run per-post catalog queries |
| module-level `BLOG_POSTS` | never mutated; enriched copies only |

## Constraints

- Business logic stays in `services.py`; the route stays thin (`openspec/config.yaml` design rules).
- FastAPI dependency injection for the DB session.
- No new dependencies; Jinja2 + HTMX only; keep the pinned requirements baseline.
- Covers are resolved through `search_products` so the editorial predicate applies (a hidden
  first product is never used as a cover).

## Files

- `services.py` — new `get_blog_posts_with_covers(session)` helper (+ shared criteria helper); no mutation of `BLOG_POSTS`.
- `main.py` — `/blog` index passes the session and serves the enriched list.
- `templates/blog_post.html` — render the cover banner when `post.hero_image` is set.
- `tests/test_catalog.py`, `tests/test_editorial_filtering.py` — new behavior tests.
- `tests/baselines/editorial_off_blog.html` — regenerate (the detail template changed).

## Task checklist and acceptance

- [ ] **T1 — Index covers**: `/blog` resolves and renders a cover per post from the first visible product.
- [ ] **T2 — Article cover**: `/blog/{slug}` renders the resolved cover as a banner.

Acceptance (Given/When/Then):

- Given a visible product matching a post's criteria, When `GET /blog`, Then that product's `image_url` appears in the card markup.
- Given a post whose criteria match no visible product, When `GET /blog`, Then the card keeps the gradient fallback (no broken `<img>`).
- Given a visible product matching the post, When `GET /blog/{slug}`, Then the cover image is rendered in the header.
- Given editorial `enforce` and the only matching product hidden, When covers are resolved, Then the cover is not derived from the hidden product.
- Given `BLOG_POSTS`, When covers are resolved, Then the module-level entries still have `hero_image is None`.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_catalog.py tests/test_editorial_filtering.py
venv/bin/python -m pytest -q --editorial-update-baselines tests/test_editorial_filtering.py   # only after an intended template diff
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

## Progress log

- Created the branch and this document before the first source write.
