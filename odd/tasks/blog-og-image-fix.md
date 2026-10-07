# Blog social image hardening: absolute og:image and honest dimensions

ODD planning artifact for this follow-up work unit. Single feature document (no separate plan file).
Follows the two non-blocking advisories from the native review of roadmap item 3
(lineage `review-2ee84e93b86bf336`, PR #58, merged as `9442b87`).

## Objective, problem, and why

The item-3 review approved the change but recorded two non-blocking findings about the
blog-post social image:

1. **R3-001 (WARNING, `main.py:545`).** `blog_post_detail` passes `post.get("hero_image")`
   straight into the template's `og_image`, and `templates/base.html` emits it verbatim.
   When a post hero is a **relative** path, `og:image`/`twitter:image` render relative and
   social crawlers cannot fetch them. In production heroes are absolute Amazon URLs, so the
   defect is latent — but the route should not depend on that.
2. **R3-002 (SUGGESTION, `templates/base.html:37-38`).** `og:image:width` and
   `og:image:height` are hardcoded to 1200x630 and emitted unconditionally, including when a
   hero image overrides `og:image` with unknown dimensions, so the declared size can
   disagree with the referenced asset.

## Authorized scope and current boundary

- Authorized: local implementation in worktree `blog-og-image-fix`, strict TDD, tests, one
  work-unit commit, regenerate the editorial golden baselines.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Base: `main` at `9442b87` (PR #58 already merged).
- Out of scope: `og:image:alt` wording; `generate_amazon_link` non-Amazon URL hijack;
  `inspiration.html` dead code; `email_utils.py` hardcoded origin; any other roadmap item.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `og_image` context | only an **absolute** `http(s)` hero becomes the post `og:image`; a relative or empty hero yields no override |
| blog post without a usable hero | `og:image`/`twitter:image` fall back to `public_origin() + /static/og-image-default.jpg` |
| blog post with an absolute hero | `og:image`/`twitter:image` equal that absolute URL |
| `og:image:width/height` | emitted only when the default asset is used (no `og_image` override); omitted when a hero overrides |
| other pages | unchanged from PR #58 |

## Constraints

- Keep the fix in the route (data normalization) and the template (conditional metadata).
- No new dependencies; Jinja2 only.
- `get_blog_post_detail` is imported **by name** into `main.py`, so any test that fakes it
  must patch `main.get_blog_post_detail`, not `services.get_blog_post_detail`.
- Noindex pages and all item-3 identity behavior stay exactly as merged.

## Files

- `main.py` — `blog_post_detail` normalizes the hero: `og_image` only when it starts with
  `http://`/`https://`, else `None`.
- `templates/base.html` — wrap `og:image:width`/`og:image:height` in `{% if not og_image %}`.
- `tests/test_seo_landings.py` — replace the old hero assertion with: (a) relative hero falls
  back to the default asset with dimensions; (b) absolute hero overrides `og:image` and omits
  dimensions.
- `tests/baselines/editorial_off_blog.html` — regenerated once (the seed hero is relative, so
  `og:image` becomes the default asset).
- `odd/tasks/blog-og-image-fix.md` — this document.

## Task checklist and acceptance

- [x] **T1 — Absolute-only hero**: `blog_post_detail` normalizes the hero, so a relative/empty
      hero never reaches `og:image` and an absolute hero does.
- [x] **T2 — Honest dimensions**: `og:image:width`/`height` are wrapped in `{% if not og_image %}`
      and appear only with the default asset; `editorial_off_blog.html` regenerated (only baseline
      that drifted).

Acceptance (Given/When/Then):

- Given a blog post whose hero is relative (`img-a1.jpg`), When `/blog/{slug}` is requested,
  Then `og:image` is `public_origin() + /static/og-image-default.jpg` with width 1200 and
  height 630.
- Given a blog post whose hero is absolute (`https://cdn.example/hero.jpg`), When
  `/blog/{slug}` is requested, Then `og:image` equals that URL and no `og:image:width` or
  `og:image:height` meta is emitted.
- Given any other page, Then its identity tags are unchanged from PR #58.

## TDD mode and verification checks

**Mode: strict TDD on.** Source: `openspec/config.yaml` (`strict_tdd: true`, `rules.apply.tdd: true`).
Runner: `venv/bin/python -m pytest`. Python 3.13 baseline unchanged.

Foreground checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_seo_landings.py tests/test_editorial_filtering.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

Baselines are regenerated once with `venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines`, then a normal run must match byte-for-byte.

## Progress log

- 2026-10-07: worktree `feature/blog-og-image-fix` created off `main@9442b87` (PR #58 merged).
- 2026-10-07: strict TDD RED (both new tests failed for the expected reason) then GREEN.
  Baselines regenerated once with `--editorial-update-baselines`; only
  `editorial_off_blog.html` changed, proving other surfaces render byte-for-byte.
  Verification: `tests/test_seo_landings.py tests/test_editorial_filtering.py` → 89 passed;
  `--ignore=tests/test_e2e.py` → 442 passed.
