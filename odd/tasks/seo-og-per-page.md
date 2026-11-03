# Per-page OG images for category landings and listings

ODD feature document for work unit 10 on branch `feat/seo-og-images`.

## Objective

Category SEO landings (`/ideas/{slug}`), `/catalog`, `/trends`, `/most-desired`,
and `/bestsellers` currently fall back to the default social image. Use the
`image_url` of the first product in the listing that has an absolute URL as the
page `og:image`/`twitter:image`, computed in the route helper
(`_catalog_context`) following the blog-post pattern (`main.py` ~641-654).

## Approved behavior

| Surface | Behavior |
| --- | --- |
| Listing pages (`_catalog_context` consumers) | `og_image` = `image_url` of the FIRST item in `result.items` whose `image_url` is an absolute `http(s)` URL |
| No product with an absolute image | fallback to `public_origin() + /static/og-image-default.jpg` (unchanged) |
| Specific `og_image` present | no `og:image:width`/`height` (already enforced by `base.html` `{% if not og_image %}`) |
| `og:image:alt` / `twitter:image:alt` | becomes overridable via `og_image_alt`; listing pages with a product image pass a page-specific alt, others keep the current default text |
| Blog JSON-LD / blog post OG | untouched (existing tests must stay green) |
| Golden rule | never invent URLs; only existing absolute `image_url` values, `startswith(("http://", "https://"))` |

## Tasks

1. TDD RED: `tests/test_og_images.py` — first-product-image og:image, fallback
   without images, no width/height with specific image, per-page alt, blog
   BlogPosting JSON-LD intact.
2. Implement in `main.py::_catalog_context` (+ alt override in
   `templates/base.html`).
3. GREEN + full suite `./venv/bin/python -m pytest tests/ -q
   --ignore=tests/test_e2e.py` (baselines only if the diff requires it).
4. One work-unit commit `feat(seo): ...`.

## Boundary

No push, no PR. Blog post route is out of scope unless a bug is evident.

## Evidence

- Commit: `986eb66` (`986eb664150b0c958cec8b1111cade36f07bada4`) on `feat/seo-og-images`.
- TDD: RED 3/6 fallando -> implementación -> GREEN 6/6.
- Suite completa: 636 passed (`pytest tests/ -q --ignore=tests/test_e2e.py`), sin baselines.
