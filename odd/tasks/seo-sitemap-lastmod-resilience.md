# SEO: sitemap lastmod resilience

Work unit 8 of the SEO roadmap (`fix/sitemap-lastmod-resilience`). URGENT:
production `/sitemap.xml` returns 500 since #81 (commit 83126a2).

## Objective, problem, and why

Since deploying lastmod support, `/sitemap.xml` 500s on Railway + Postgres
(`curl https://regalame.app/sitemap.xml` → 500) while local SQLite tests pass.
robots.txt advertises the sitemap and Search Console already reported 5xx.

Root cause by elimination: `list_categories()` also runs on /catalog and
/ideas/{slug} (both 200 in prod), so the only sitemap-only queries are the new
`catalog_lastmod()` / `category_lastmod()`. Both end in
`session.exec(select(func.max(...))).one()`. `.one()` raises
`NoResultFound` on zero rows and is driver-sensitive on single-column
aggregate selects; `.first()` returns None instead of raising.

Defense in depth: lastmod is freshness metadata, never worth a 500. The
sitemap must always serve 200 with all URLs, degrading to no `<lastmod>`
when the aggregate fails or when any single category lastmod fails.

## Approved design

1. `catalog.py`: `.one()` → `.first()` in `catalog_lastmod` and
   `category_lastmod`.
2. `main.py` `sitemap_xml`: wrap aggregate lastmod and per-category lastmod in
   `try/except Exception` → `logger.exception("sitemap lastmod failed")` and
   degrade to no lastmod. URLs are never lost to a freshness failure.
3. `main.py`: module logger (`logging.getLogger(__name__)`) if absent.

Scope: local implementation, TDD, tests, one work-unit commit on
`fix/sitemap-lastmod-resilience`. Not authorized: push, PR.

## Tasks

- [x] T1 (RED): `tests/test_sitemap_resilience.py` — aggregate lastmod
      raising → 200 without lastmod; category lastmod raising → 200 with all
      URLs present; empty table → `catalog_lastmod`/`category_lastmod`
      return None without raising.
- [x] T2 (GREEN): `.first()` in catalog.py; try/except degrade in main.py.
- [x] T3: full suite `pytest --ignore=tests/test_e2e.py` green.
- [x] T4: single commit `fix(seo): ...`.

## Evidence

- T1 RED observed: both exception tests 500'd (`RuntimeError` propagated by
  `main.py:217`); empty-table test already passed on SQLite (`MAX` over zero
  rows returns `(None,)`), kept as a driver-regression guard.
- T3 GREEN: `tests/test_sitemap_resilience.py` 3 passed; full suite
  `619 passed` in 25.11s (`--ignore=tests/test_e2e.py`).
- One caveat, honestly stated: the true Postgres failure mode could not be
  reproduced locally (SQLite-only tests), so the production 500 root cause is
  root-cause-by-elimination (see Objective) plus defense in depth. After
  deploy, `logger.exception("sitemap lastmod failed")` will write the exact
  traceback to Railway logs if anything still fails.
- Commit: the tip of `fix/sitemap-lastmod-resilience`: `fix(seo): never 500 the sitemap; degrade lastmod and
  log the cause` (branch `fix/sitemap-lastmod-resilience`, no push/PR).
