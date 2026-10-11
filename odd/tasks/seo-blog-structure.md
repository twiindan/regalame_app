# SEO Blog Structure — thematic H2 sections and richer schema

Branch: `feat/seo-blog-structure`

## Goal

Blog post pages (`/blog/{slug}`) currently render one flat product grid: zero
`<h2>` headings and one `<h3>` per product card. Add thematic `<h2>` sections
that group the products, ensure the BlogPosting JSON-LD is complete, and emit
FAQPage schema when a post defines FAQ data. No push, no PR.

## Tasks

- [x] T1 — Product grouping: add `group_blog_products` in `services.py`
      (by `category` when a post mixes categories, else by price tiers using
      `price_numeric`; no-price products fall into a trailing "Precio
      variable" section; empty list returns no sections). Test-first.
- [x] T2 — Template `blog_post.html`: render one `<section>` per group with an
      `<h2>` and the existing product cards (`<h3>`) inside; keep the
      load-more behavior working across sections (namespace counter).
- [x] T3 — BlogPosting JSON-LD: verify existing block; add absolute `url`
      (via `social_url(canonical_url)`) alongside `mainEntityOfPage`;
      `datePublished` already rendered when present (no post defines it yet).
- [x] T4 — FAQPage JSON-LD: conditional on `post.faq` (no post defines FAQ
      data today, so live pages emit nothing; hook is tested). Report the
      missing FAQ data to the user; authoring neutral FAQs is a follow-up.
- [x] T5 — Tests: new `tests/test_blog_structure.py` (grouping unit tests +
      page-level h2/h3 structure + FAQPage conditional); run
      `pytest tests/ -k blog` plus related suites (`test_seo_landings.py`,
      `test_christmas_guide.py`, editorial baselines) and the full suite.
- [x] T6 — Commit(s): one work-unit commit, Conventional Commit
      `feat/seo-blog-...` style matching repo history. No push, no PR.

## Evidence

- T1/T2/T3/T4/T5: commit `35d56bd` — `feat/seo-blog-h2-sections: group blog
  products into thematic h2 sections and complete post schema`
  (5 files changed, 232 insertions, 2 deletions).
- Test results at commit time: 461 passed, 3 skipped (full suite);
  `pytest tests/ -k blog` → 12 passed.
