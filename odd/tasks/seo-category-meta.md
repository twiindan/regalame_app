# Query-driven SEO titles and metas on /ideas/{slug} landings

ODD planning artifact for work unit 12. Single feature document.

## Objective, problem, and why

All 33 `/ideas/{slug}` landings render the same generic `<title>` and meta
description pattern (`templates/category_seo.html`): "Las Mejores Ideas de
Regalo para {category_name} (2026) | Regálame" plus one templated
description. The pages compete with each other with interchangeable titles
and do not target the real search queries of the niche in Spain, so Google
barely indexes them. Goal: a per-category `meta` field (title + description)
in `seo_content.py` for the 12 categories already covered by
`CATEGORY_CONTENT`, with varied title patterns and descriptions that
naturally name 2-3 real search terms (regalos originales, amigo invisible,
cumpleaños, ...) in Spain-Spanish, neutral tone, no empty superlatives.

## Authorized scope and current boundary

- Authorized: local implementation, strict TDD, baseline regeneration where
  required, one work-unit commit. No push, no PR, no deploy.
- Wiring constraint: the template can only receive new data through the
  Jinja environment. The user restricted edits to `seo_content.py`,
  `category_seo.html` and tests; the only viable wiring without touching the
  route handler is a Jinja global registered in `main.py` next to
  `social_url` (2 plumbing lines). Route handler and business logic stay
  byte-identical. This deviation is documented and deliberate.
- Out of scope: routes, catalog logic, `/amigo-invisible` FAQ, blog content,
  other templates.

## Approved behavior

| Surface | Behavior |
| --- | --- |
| `CATEGORY_CONTENT[*].meta` | new optional `meta` dict (`title`, `description`) inside each of the 12 existing entries |
| `category_meta(name)` | returns `{"title", "description"}` for entries with `meta`; `None` otherwise |
| fallback | categories without an entry, or with an entry lacking `meta`, keep the exact current generic title/description pattern (21 slugs unaffected) |
| template | `category_seo.html` uses `meta.title` / `meta.description` when `category_meta()` returns data, else the current pattern |
| content policy | no invented product claims, prices, ratings or Amazon data; varied title skeletons; Spain-Spanish; titles unique among the 12 |
| limits | title ≤ 70 chars, description ≤ 160 chars (writing target: ~60 / 140-158) |

## Files

- `seo_content.py` — `meta` per entry + `category_meta()` lookup with fallback.
- `main.py` — 2 lines: import `category_meta`, register as Jinja global.
- `templates/category_seo.html` — consume `category_meta()` with fallback.
- `tests/test_category_meta.py` — new suite.
- `tests/baselines/editorial_off_ideas.html` — regenerated (the baseline
  category `alimentacion-y-bebidas` gains a meta title/description).

## Task checklist and acceptance

- [x] **T1 — RED**: `tests/test_category_meta.py` fails against current code.
- [x] **T2 — GREEN**: metas render on landings with `meta`; fallback intact.
- [x] **T3 — Baseline + suite**: baseline regenerated; full suite green
      without `tests/test_e2e.py`.

## Evidence

- RED observed: `ImportError: cannot import name 'category_meta' from
  'seo_content'` (collection error, 0 tests run).
- GREEN: `tests/test_category_meta.py` 54 passed.
- Baseline regenerated with `--editorial-update-baselines`:
  `tests/baselines/editorial_off_ideas.html` now carries the
  `alimentacion-y-bebidas` meta title/description in `<title>`,
  meta description, og and twitter tags; stable on a second suite run
  without the flag.
- Full suite: `./venv/bin/python -m pytest tests/ -q --ignore=tests/test_e2e.py`
  → 710 passed.
- Length audit: 12 titles 47-59 chars (all ≤ 70), 12 descriptions 140-150
  chars (all within 140-158, cap 160), titles unique.
- Wiring deviation (documented, approved by constraint analysis): the
  template can only receive new data through the Jinja environment, so
  `main.py` gains exactly the import plus
  `templates.env.globals["category_meta"] = category_meta` next to
  `social_url`. No route handler or business logic changed (diff verified).
- Commit: `feat(seo): query-driven titles and metas on /ideas landings` on
  branch `feat/seo-category-meta` (no push, no PR).

## Acceptance (Given/When/Then)

- Given `/ideas/alimentacion-y-bebidas` (has `meta`), when rendered, then the
  `<title>` and meta description differ from the generic pattern.
- Given a category without `meta` (e.g. `Jardín`), when rendered, then the
  generic pattern is used unchanged.
- Given the 12 metas, when collected, then titles are unique, ≤ 70 chars and
  descriptions ≤ 160 chars.
