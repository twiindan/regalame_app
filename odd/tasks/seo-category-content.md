# Unique per-category SEO content on /ideas/{slug} landings

ODD planning artifact for work unit 11. Single feature document (no separate plan file).

## Objective, problem, and why

The category landings (`/ideas/{slug}`, `templates/category_seo.html`) render a
`category_guide` block (title + intro + tips) and a category FAQ from
`seo_content.py`. Today `category_guide(name)` and `category_faq(name)` are
100% templated: the same text with `{name}` interpolated is served for all
categories. Google sees near-identical pages across categories (thin/duplicate
pSEO). Goal: unique, topic-specific guidance per category without inventing
numbers, ratings, superlatives or fabricated claims (strict repository
editorial policy).

## Authorized scope and current boundary

- Authorized: local implementation on `feat/seo-category-content`, strict TDD,
  baseline regeneration where required, one work-unit commit.
- Not authorized: push, PR, merge, deploy, or any remote operation.
- Out of scope: `related_posts` matching, `BLOG_POSTS` content, template
  structure, `/amigo-invisible` FAQ, `main.py` route logic.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `CATEGORY_CONTENT` | new slug-keyed dict in `seo_content.py` with topic-specific `intro`, `tips` (4-5) and `faq` (2-3) for the high-value categories |
| `category_guide(name)` | looks up `CATEGORY_CONTENT` via `catalog.slugify(name)` normalization; falls back to the current generic text only when there is no entry |
| `category_faq(name)` | same lookup; specific questions when an entry exists, generic fallback otherwise |
| fallback | categories without an entry keep the exact current generic guide/FAQ |
| content policy | no prices, currency symbols, ratings, percentages, "best/world's best" claims, discounts or invented numbers anywhere in `CATEGORY_CONTENT` |
| coverage | at least 10 categories with specific content |

## Target categories (slugs derived via `catalog.slugify` from real DB category names)

`electronica`, `belleza`, `hogar-y-cocina`, `moda`, `juguetes-y-juegos`,
`deportes-y-aire-libre`, `libros`, `alimentacion-y-bebidas`, `videojuegos`,
`productos-para-mascotas`, `bebe`, `informatica` (12 entries).

## Files

- `seo_content.py` — `CATEGORY_CONTENT`, lookup helpers, fallback wiring.
- `tests/test_category_content.py` — new TDD suite (specific vs generic,
  fallback intact, FAQ present, anti-claim sweep over all content strings).
- `tests/baselines/editorial_off_ideas.html` — golden baseline regenerated
  (`--editorial-update-baselines`) because `/ideas/alimentacion-y-bebidas`
  gains specific content.

## Task checklist and acceptance

- [x] **T1 — RED**: `tests/test_category_content.py` fails against current code.
- [x] **T2 — GREEN**: specific guide/FAQ for entries, generic fallback intact.
- [x] **T3 — Policy sweep**: anti-claim test passes over all `CATEGORY_CONTENT` strings.
- [x] **T4 — Baselines + suite**: full suite green without `tests/test_e2e.py`.

## Evidence

- RED observed: `ImportError: cannot import name 'CATEGORY_CONTENT'` (20 tests, 0 pass).
- GREEN: `tests/test_category_content.py` 20 passed.
- Full suite: `./venv/bin/python -m pytest tests/ -q --ignore=tests/test_e2e.py` → 656 passed.
- Baseline regenerated: `tests/baselines/editorial_off_ideas.html` (guide intro, tips, FAQ and
  FAQPage JSON-LD of `/ideas/alimentacion-y-bebidas` now show the topic-specific content).
- Commit: feat(seo) work-unit commit on `feat/seo-category-content` (no push, no PR).

Acceptance (Given/When/Then):

- Given `category_guide("Electrónica")` (name form) or `category_guide("electronica")` (slug form),
  when called, then intro/tips differ from the generic output.
- Given a category without an entry (e.g. "CD y vinilos"), when called, then output equals the
  current generic text exactly.
- Given the full suite, when run without e2e, then all tests pass.
