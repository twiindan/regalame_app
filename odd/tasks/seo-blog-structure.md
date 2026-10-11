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

- T1–T5: commit `ebf0c9a` — `feat(seo): group blog products into thematic h2
  sections and complete post schema` (6 files changed, 381 insertions(+),
  10 deletions(-)).
- Test results at commit time: full suite `pytest tests/ --ignore=tests/test_e2e.py`
  → 573 passed; `pytest tests/ -k blog` → 70 passed. test_e2e.py excluded:
  pre-existing env limitation (playwright + live server not available).
- `tests/baselines/editorial_off_blog.html` regenerated intentionally with
  `--editorial-update-baselines` (new h2 section markup + BlogPosting url).
- Native review preflight (gentle_review inspect): blocked —
  `package-local-binary-missing`; no lineage created, no mutation. Install
  with `node scripts/install-gentle-ai.mjs` from the gentle-pi package dir
  if native review is wanted for this candidate.
- Follow-up: no post in blog_config defines `faq` or `date_published`; the
  FAQPage hook is tested but emits nothing until FAQ data is authored.
