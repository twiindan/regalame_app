# Feature: SEO Product + Offer JSON-LD (WU9)

Branch: `feat/seo-product-offer`

Add schema.org `Product` + `Offer` JSON-LD to the public category landing pages
(`/ideas/{category_slug}`, template `category_seo.html`) so Google can surface
product rich results. Strict repo policy: no reviews and no ratings exist, so
`aggregateRating` / `review` must never be emitted. Products without a parsed
price emit no `offers` at all (never invent a price).

## Design decisions

- Enrich the existing `CollectionPage.mainEntity.ItemList`: each `ListItem`
  gains an `item` of type `Product` instead of adding a second `ItemList`
  (avoids duplicate ItemList markup).
- `Product`: `name` (title), `image` only when `image_url` exists,
  `offers` only when `price_numeric` is not `None` (an `Offer` without a price
  is flagged by Google, so omission validates better).
- `Offer`: `price` = `price_numeric`, `priceCurrency` = `EUR` (fixed: Spain),
  `url` = Amazon affiliate URL.
- Scope: category SEO landings only. `/bestsellers`, `/trends`, `/most-desired`
  share `catalog.html` and are out of this work unit.

## Tasks

- [ ] T1 — RED: `tests/test_product_schema.py` parses JSON-LD from a category
      landing with priced products (Product + Offer with price + EUR), from a
      product without price (no offers, nothing invented), image omitted when
      missing, no ratings/reviews, and JSON always parseable.
- [ ] T2 — GREEN: enrich `templates/category_seo.html` ItemList with
      `Product`/`Offer` items following existing `tojson` conventions.
- [ ] T3 — Full suite green: `./venv/bin/python -m pytest tests/ -q --ignore=tests/test_e2e.py`.
- [ ] T4 — Work-unit commit `feat(seo): ...`.

## Evidence

(pending)
