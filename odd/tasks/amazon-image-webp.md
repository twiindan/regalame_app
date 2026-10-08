# Amazon product images to WebP (mobile performance, roadmap item 6 follow-up)

Work unit after `odd/tasks/asset-build-hardening.md` and `odd/tasks/asset-tests-docs.md`.
This is the only ODD planning artifact for this work unit.

## Objective and problem

Amazon product images are the heaviest remaining asset class on the catalog surfaces. They
are third-party binaries served from `images-eu.ssl-images-amazon.com`; Cloudflare (the edge)
does not transform or compress images it does not originate, and the repo's no-Node /
no-proxy convention rules out a resizer. Measured `Content-Length` on a 24-image catalog
sample: **397 KB of JPEG per page**.

## Why this approach (decision, resolved)

User chose **WebP at the same resolution**. Amazon's image CDN serves WebP when the `_AC_`
transform segment gains the `_FMwebp_` marker, at the SAME resolution and lower payload:
measured **−37..44%** (Amazon's default WebP quality is smaller than `_QL70_`).

Rejected alternatives:
- **AVIF** (`_FMavif_`): only ~−5% on the same sample.
- **Downscaling** (e.g. `UL600/SR600,400` → `UL400/SR400,267`): −37% alone, but trades
  DPR/quality; and forcing a square `SR320,320` on `UL300/SR300,200` images makes Amazon
  re-crop to square and **increase** bytes. Not worth the quality risk for the win.
- **Any proxy / resizer / Cloudflare Images**: adds infra and breaks edge caching, against
  the no-Node/no-proxy convention.

## Scope

- New stdlib-only helper `amazon_webp_url(url)` in `image_urls.py`.
- Jinja filter `amazon_webp` registered in `main.py` beside the existing globals.
- Applied ONLY to product/wish `<img src>` (catalog grid, blog product grid + hero,
  dashboard carousels, wishlist items, blog index cover).
- **Out of scope**: `manual_image` hidden inputs (persist the URL verbatim), the
  public-profile JSON-LD image (`templates/public_profile.html:113`), `og:image` /
  `twitter:image` (`templates/base.html`), `inspiration.html` (dead code, wrong field),
  `srcset`/DPR buckets, and a `<picture>` JPEG fallback.

## Constraints

- No Node/npm/bundler; no new runtime dependency; stdlib only.
- The guard MUST be a no-op for: non-Amazon hosts, paths without `._AC_`, non-`.jpg`,
  falsy values, and already-rewritten URLs (idempotent).
- Delivery is user-owned: **no commit / push / PR**.
- Strict TDD (source: `openspec/config.yaml`), runner
  `python -m pytest -q --ignore=tests/test_e2e.py`.

## Tasks

- **T1** — Helper `image_urls.py::amazon_webp_url`. Write tests first (RED), then implement.
- **T2** — Register the `amazon_webp` filter in `main.py` and apply it at the six product
  `<img src>` render sites.
- **T3** — Integration test: rendered catalog HTML has `_FMwebp_` in the product `<img src>`
  but the `manual_image` value stays the original URL.
- **T4** — Run the full suite; update this doc and the Engram mirror.

## Acceptance criteria

- Amazon `._AC_..._.jpg` product URLs render with `_FMwebp_`.
- Non-Amazon / falsy fixtures render exactly as before (golden baselines unchanged).
- `manual_image` values and JSON-LD / `og:image` keep the ORIGINAL URL.
- All tests green; no new dependency.

## Checks

- `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
- Rendered HTML contains `_FMwebp_` on a product surface, and not on `manual_image`.

## Delivery

No commit. User owns commit/push/PR.

## Progress

- [x] T1 helper + unit tests
- [x] T2 filter wiring + template sites
- [x] T3 integration test
- [x] T4 full suite + docs/mirror

## Progress / results

- `venv/bin/python -m pytest -q tests/test_image_urls.py` — **13 passed** (12 unit
  cases + 1 catalog integration case).
- `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py` — **533 passed, 0 failed**
  (15.8s). Existing golden baselines (`tests/test_editorial_filtering.py`,
  `tests/baselines/*.html`) stayed green and unchanged: their fixtures use
  non-Amazon URLs (`img-*.jpg`, `cdn.example`), where the guard is a no-op.
- Eight `<img src>` sites rewritten, all others untouched. `manual_image` hidden
  inputs, `public_profile.html` JSON-LD `"image"`, and `base.html` `og:image` /
  `twitter:image` keep the original URL (verified by grep).
- TDD: RED observed first as `ModuleNotFoundError: No module named 'image_urls'`,
  then the integration assertion failed before filter wiring; GREEN after the
  helper + filter were added.
- Delivery remains user-owned: nothing committed/pushed/PR'd.

## Native review (RDD)

- Tier: **medium** (9 paths, 266 changed lines; reason `executable_change` in image_urls.py).
- Settings: `--consent=relay`, workspace projection, 1 selected lens (`review-reliability`).
- Outcome: **approved** — lineage `review-b24b22e45f22d259`, authority burned
  (`gentle-ai.review-acknowledged/v1`, consumed revision
  `sha256:c2744365a589b6a3eacf17ed11c47bbbe2b500da3dcb13fcc199ade1ed6a1167`).
- Non-blocking findings (separate later work; do NOT re-run review for this candidate):
  - **R3-001** (`image_urls.py:37-41`): the `urlsplit` `ValueError` failure path is never
    exercised by tests — malformed-URL handling is unproved.
  - **R3-002** (`image_urls.py:34`): the idempotency guard matches `_FMwebp_` anywhere in the
    URL, so a marker in the query/fragment would skip a valid rewrite.
