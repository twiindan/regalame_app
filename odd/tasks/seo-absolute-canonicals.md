# SEO absolute canonicals and brand entity schema

Work unit 2 of the persisted SEO plan (`odd/tasks/seo-improvements.md` line of work). Audit findings: `templates/base.html` emits `<link rel="canonical" href="/ideas/belleza">` with a RELATIVE href (Google prefers absolute URLs), and only a `SoftwareApplication` schema exists site-wide; `WebSite`/`Organization` entity schema is missing.

## Objective, problem, and why

1. Relative canonicals are resolved against the rendering origin by crawlers, which is fragile (mirrors, proxies, scheme differences). The repo already has `public_origin()` as the single source of truth and `social_url()` as the absolutizer used by `og:url`/`twitter:url`, but the canonical link bypasses it.
2. Google builds entity/brand understanding from `WebSite` and `Organization` structured data.

**Correction found while exploring:** the audit was stale — `templates/index.html` already emits `WebSite` (with SearchAction) and `Organization` via `extra_schema`, but ONLY on the home page (commit `7fdf08c`). The approved work therefore moves those blocks into `templates/base.html` as ONE combined `@graph` JSON-LD (site-wide entity identity), and removes them from `index.html` so the home page does not duplicate `WebSite`/`Organization`.

## Approved scope and boundary

- Authorized (user request, 2026-xx): absolute canonicals; `WebSite` + `Organization` JSON-LD in `templates/base.html`; tests updated; full suite run with `--ignore=tests/test_e2e.py`; ONE work-unit commit on `feat/seo-absolute-canonicals`.
- Not authorized: push, PR, merge, deploy, any remote operation.
- Base: `main` merged state at `ae79a38`; branch `feat/seo-absolute-canonicals` already created by the user.

## Design decisions

- **Normalize in `templates/base.html`, not per-route in `main.py`**: change the canonical href to `{{ social_url(canonical_url) }}`. One line, single source of truth, consistent with how `og:url`/`twitter:url` already normalize, and it fixes every route at once (`/blog`, `/blog/{slug}`, `/ideas/{slug}`, `/ideas/{slug}?page=N`). `social_url()` passes already-absolute values through (home and `/amigo-invisible` set `canonical_url` to `public_origin() + ...`), so no double-prefix risk.
- **noindex pages keep emitting no canonical**: the `{% if canonical_url %}` guard is untouched; `_catalog_context` continues to set `canonical_url=None` for noindex pages.
- **Entity schema as two separate JSON-LD scripts (evaluated choice)**: a single `@graph` block was tried first but breaks the site-wide test convention that each JSON-LD script is one flat node (`item["@type"]`), used by `test_blog_structure.py`, FAQ confinement tests, etc. Two sibling scripts (`WebSite` with SearchAction, `Organization`) keep the same per-script node shape as every other schema on the site (`SoftwareApplication`, `BlogPosting`, `FAQPage`), avoid helper churn, and carry no SEO penalty — Google reads scripts independently. Moved from `index.html` into `base.html`; exactly one `WebSite` and one `Organization` per page.
- Out of scope (follow-up candidates): absolute URLs in `blog_post.html` BreadcrumbList items.

## Files

- `templates/base.html` — canonical href via `social_url()`; new combined `@graph` entity JSON-LD block (moved from `index.html`).
- `templates/index.html` — `extra_schema` block removed (entity schema now site-wide in `base.html`).
- `tests/test_seo_landings.py` — flip `test_category_retains_its_existing_relative_canonical` to absolute; add absolute-canonical coverage for indexable pages; add WebSite/Organization schema tests.
- `odd/tasks/seo-absolute-canonicals.md` — this document.

## Task checklist and acceptance

### T1 — Absolute canonicals (test-first)

- [ ] Flip the category relative-canonical test and add absolute-canonical coverage; observe RED.
- [ ] `templates/base.html`: `href="{{ social_url(canonical_url) }}"`; observe GREEN.

Acceptance:

- Given any indexable page, When rendered, Then exactly one `link[rel=canonical]` whose href is absolute (starts with the configured origin).
- Given a noindex page (`/catalog`, filtered catalogs), Then no canonical link is emitted (unchanged).
- Given `DOMAIN_URL` overridden, Then the canonical href follows the configured origin (no hardcoded default).

### T2 — Brand entity schema (test-first)

- [x] Add WebSite/Organization schema test; observe RED.
- [ ] Add entity JSON-LD to `templates/base.html` (two sibling scripts, moved from `index.html`); observe GREEN.

Acceptance:

- Given any page, Then exactly one JSON-LD item with `@type` `WebSite` and exactly one with `@type` `Organization` (same `@graph`), both named `Regálame`, with `url` from `public_origin()`, `logo` pointing at `/static/og-image-default.jpg`, and the WebSite SearchAction preserved.
- Given `DOMAIN_URL` overridden, Then no `regalame.app` hardcode appears (existing hardcoded-origin test stays green).

### T3 — Verification and work-unit commit

- [ ] Full suite `python -m pytest --ignore=tests/test_e2e.py` green.
- [ ] One commit `feat(seo): ...` on `feat/seo-absolute-canonicals`; no push, no PR.

## Evidence

(commit hash recorded after T3)
