# Exploration: AI-assisted gift catalog curation (`curacion-regalos-ia`)

Status: exploration only — no implementation. All claims verified against the worktree at commit `33754d3` (worktree `regalame_gemini3-worktrees/curacion-regalos-ia`).

## 1. Problem

The public catalog is a raw, uncurated mirror of three Amazon.es ranking lists. It contains many items that are weak gift ideas (office supplies, DIY tools, "Amazon Renewed", "Climate Pledge Friendly", "Productos Handmade" — real categories observed in the data), yet the UI presents them as gift recommendations ("Lo más regalado este año"). There is no editorial layer of any kind: what Amazon lists is what users see. The goal is an AI-assisted classification that decides, per product, whether it is suitable as a gift idea, and a filtering layer that applies those decisions across all public product surfaces — offline, without touching the commercial import pipeline or user wish lists.

## 2. Current-state evidence (verified, with exact references)

### 2.1 Ingestion has no editorial control

- `scraper.py:36-43` — `SECTIONS` = bestsellers / trends / desired (list keys; desired ↔ file `amazon_mas_deseados_total.json`).
- `scraper.py:46-68` — `get_all_category_links` scrapes **every** sidebar category until a "Ver más" stop word. No allowlist, no editorial filter.
- `scraper.py:78-80` — up to 50 items per category (`items[:50]`), all categories concatenated per list, so `ProductList.rank` is the position across the entire list, not per category.
- Real data (computed from the three repo JSONs): **3,677 distinct ASINs** (bestsellers 1,432 / desired 1,315 / trends 1,278), **32 distinct categories**, including non-gift categories like "Oficina y papelería", "Bricolaje y herramientas", "Amazon Renewed", "Climate Pledge Friendly".

### 2.2 Import is a blind commercial upsert

- `catalog.py:236-321` — `import_from_json` upserts by ASIN (`extract_asin`, `catalog.py:45-51`), and on update **overwrites** `title`, `title_normalized`, `category`, `category_slug`, price, `scraped_at` every refresh (`catalog.py:295-305`). There is no gift-suitability notion anywhere.
- Consequence for fingerprints: `Product.category` is **last-write-wins** across sources. "Observed categories" as a classification input is lossy today — only the category from the most recently imported source survives (`catalog.py:299-300`).
- `catalog.py:192-221` — `deactivate_absent_products` only flags `is_active=False`; it never deletes.

### 2.3 One shared query path (good news for centralization)

- `catalog.py:114-178` — `search_products` builds a `filters` list once (`catalog.py:127-143`), runs `count` with it (`catalog.py:145`), then orders/pages the same filter set (`catalog.py:168-170`). An editorial predicate added to `filters` automatically corrects totals, pagination and every caller.
- Callers (CodeGraph blast radius: **30 call sites**): dashboard `main.py:213-215` (random samples per source), `/catalog` `main.py:332-353`, `/trends` `main.py:358-371`, `/most-desired` `main.py:374-387`, `/bestsellers` `main.py:390-403`, SEO category pages `/ideas/{slug}` `main.py:413-437`, blog lists `services.py:185-215` (`get_blog_post_detail` paginates **all** matching products via `search_products`).
- Surfaces that do **not** go through `search_products` and must stay untouched: wish lists (`Wish` model `models.py:82-95`, routes `main.py:784-865`) — `Wish` is independent of `Product`.
- Leak points outside `search_products`:
  - `catalog.py:181-189` — `list_categories` groups over **all** active products. After editorial filtering, navigation and the sitemap (`main.py:119-127`) can advertise categories whose pages are now empty.
  - `services.py:212-213` — blog hero image falls back to `products[0].image_url`; filtering changes which product is first.

### 2.4 Editorial claims without evidence

- `templates/dashboard.html:157` — bestsellers carousel is labeled "Lo más regalado este año". The only evidence behind it is Amazon's own bestseller rank (`ProductList.list_key='bestsellers'`); "regalado" (gifted) is asserted, never measured. Curation filters products but does not by itself fix this copy (separate product decision).

### 2.5 Data model

- `models.py:105-118` — `Product` has a single `category` / `category_slug`; no editorial state, no collection, no context.
- `models.py:120-125` — `ProductList(product_id, list_key, rank)` with unique constraint `(product_id, list_key)`; rank is per-list (global across categories within the list), confirmed by `_rank_subquery` (`catalog.py:101-111`, min rank across lists or per source).

### 2.6 Job patterns to reuse

- `jobs/refresh_catalog.py` is the template for a second job: plain CLI (`main()` at `jobs/refresh_catalog.py:164-170`), `run(session, scrape_fn=..., dry_run=..., ...)` seam with injectable dependency for tests (`:103-121`), health guards — `MIN_HEALTHY_RATIO = 0.5` (`:18`), `classify` (`:58-74`), deactivation only on a complete healthy run (`:147-151`). `jobs/` package already exists (`jobs/__init__.py`).
- Deployment is web-only (`Procfile`: `web: uvicorn main:app`); jobs run out-of-band via Railway cron (git history: `f01c55d docs: warn about the cron restart loop and Railway cron constraints`). A long-running classification job inherits those cron constraints.

### 2.7 Tests, migrations, environment

- `tests/conftest.py:14-25` — SQLite in-memory + `StaticPool` + `SQLModel.metadata.create_all`. **Alembic migrations are never exercised by tests.** A new table works in tests via `create_all` but the migration must be written and verified separately (CI runs only pytest, `.github/workflows/ci.yml:50`).
- Alembic: 10 migrations, single linear chain, **head = `9f1c7b2a4d3e`** ("add product tables"; verified nothing references it as `down_revision`). A new migration must set `down_revision = "9f1c7b2a4d3e"`. `alembic/env.py` imports `models`, so autogenerate is available.
- `requirements.txt` pins `sqlmodel==0.0.27` with an explicit warning: 0.0.47+ maps `datetime` to TZ-aware columns and breaks the naive datetimes stored here (`models.py:7-14` `utcnow_naive`). Any new model MUST keep the naive-datetime convention.
- **No AI provider integration exists**: no `openai`/`anthropic`/HTTP-LLM code in the app (verified by grep over the repo — only irrelevant matches inside `venv` site-packages) and no AI SDK in the venv. Production deps include `requests` (`requirements.txt`); `httpx` is dev-only (`requirements-dev.txt`).
- Config convention is plain `os.getenv` at module level (`main.py:42,50,82`, `services.py:85`, `email_utils.py:8,16`, `database.py`). No settings module exists.
- Python: CI pins 3.13 (`.github/workflows/ci.yml:38`); system `python3` here is 3.14.0; **the main repo has a working venv (Python 3.13.5)** at `/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv`; the worktree has none. Verified: `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py` run from the worktree → **128 passed in 5.31s**.

## 3. Settled direction vs. the code — verdict

No contradiction found between the seven settled points and the code. All are compatible; the notes below refine where the code adds constraints:

1. **Offline classification** — compatible. Nothing in the request path calls an LLM today; the only network call at request time is `scrape_metadata` for wish URLs (`services.py:30`), which stays untouched.
2. **Per-ASIN editorial record** — requires a new model + migration (head `9f1c7b2a4d3e`). Design gap to resolve: "observed categories" input. `Product.category` is last-write-wins (`catalog.py:299-300`); multi-source category history is **not stored today**. Either the fingerprint uses `title + Product.category` (lossy but simple), or the classifier input must be captured per source at import/refresh time (new state). Open design decision, not a contradiction.
3. **Cache discipline** — compatible. Price/rank/`scraped_at` are already separate columns; a fingerprint over `title + observed categories` naturally ignores them. `import_from_json` overwrites `title` on every refresh (`catalog.py:295-296`) — a genuine title change re-triggers classification, which is the intended semantic. Failure-not-cached is new behavior; nothing in the code caches failures today.
4. **Additive table + manual override** — compatible. Since `import_from_json` only touches `Product`/`ProductList` (`catalog.py:236-321`), an editorial table it never writes to satisfies "importer never writes override" by construction.
5. **Centralized filtering in `search_products` before count** — compatible and cheap: one predicate in the shared `filters` list (`catalog.py:127-143`) fixes count, pagination and all 30 call sites at once. Two leaks remain outside this path and need explicit scope: `list_categories` (`catalog.py:181-189`) and the sitemap (`main.py:119-127`). Raw import health metrics (`refresh_catalog.baseline_counts`, `jobs/refresh_catalog.py:21-26`) count `ProductList` rows, not filtered results — editorial filtering cannot corrupt them. `ProductList` rows are never deleted by curation (import only deletes/rewrites them per list; curation must not touch them).
6. **Separate classification job** — compatible; `jobs/refresh_catalog.py` is the established pattern (CLI + injectable seam + dry-run). Rate/concurrency limits (60 rpm/key, 5 concurrent for the candidate models) are external constraints from NaN Builders docs — **not verifiable from this repo**; treat as given. At 60 rpm, a full backfill of 3,677 products is ≥ ~61 min at one product per request; resumability is mandatory, not optional.
7. **Rollout** — compatible. Shadow mode + config switch fit the `os.getenv` convention; `--dry-run` precedent exists in both `import_catalog.py:19-23` and `refresh_catalog.py:157-159`. The direction's two distinct modes (no-network dry-run vs. real-but-non-persisting) have no precedent in the repo and both need explicit design.

## 4. Candidate approaches

### A. Separate editorial-decision table + centralized query filter (recommended)

New table keyed by ASIN (or `product_id`) holding state (`eligible` / `contextual` / `excluded` / `unknown`, with unknown never promoted), primary collection, context, reason, model id, policy version, input fingerprint; plus optional manual-override rows that always win. Filtering = one predicate added to `search_products`' shared `filters` list, gated by a config switch.

- Pros: strictly additive (matches "additive table via Alembic"); importer cannot touch it by construction; preserves import health counts and `ProductList` rows; resumable job is natural (missing row = pending); 30 call sites fixed in one place; manual override needs no importer change.
- Cons: one extra `EXISTS` per catalog query (negligible at 3.7k products); two leak surfaces (`list_categories`, sitemap) need separate handling; tests must add the table to `create_all` (automatic via `models.py`) while the migration is verified by hand.

### B. Editorial columns on `Product`

- Pros: no JOIN; trivial queries.
- Cons: `import_from_json` upserts `Product` and overwrites fields wholesale (`catalog.py:295-305`) — it would have to be taught to preserve editorial state, coupling the commercial import to curation (exactly what the settled direction forbids); editorial failures become product-row mutations; no room for policy versioning without more columns. Rejected.

### C. Filter after the query (route/template level)

- Pros: zero schema change.
- Cons: totals/pagination computed pre-filter are wrong (`catalog.py:145-149`); logic duplicated across 30 call sites; sitemap/categories still leak excluded items. Rejected.

### D. Pre-filtering at ingestion (don't import unsuitable products)

- Pros: single choke point.
- Cons: merges two jobs into one; makes the import health guards (`jobs/refresh_catalog.py:58-90`) depend on an LLM's availability; destroys the ability to re-filter retroactively when the policy changes; contradicts the settled direction (separate job, shadow mode). Rejected.

## 5. Open product decisions (must be settled before spec)

1. **Semantics of `contextual`**: excluded from general surfaces but included under a matching context filter (e.g., `/ideas/bebe`)? Or visible everywhere with a badge? This changes the filter SQL and the UI.
2. **Meaning of "unknown is not promoted"**: unknown items stay visible but sink in ordering? Or are treated exactly like eligible until classified (equivalent to shadow-mode default)? Concrete ordering rule needed.
3. **Filter mode semantics**: blacklist (drop `excluded`, show everything else — site never empties) vs. whitelist (show only `eligible` — site is empty until backfill). Shadow mode suggests blacklist-on-enforce; needs an explicit decision.
4. **Empty categories after filtering**: keep nav/sitemap entries with an empty state, or suppress categories with zero visible products (affects `list_categories`, sitemap, SEO)?
5. **Fingerprint inputs**: `title` only, or `title + last observed category`? And should a category flip (source overwrite, `catalog.py:299-300`) reclassify? (Arguably yes — it is a content change — but it must be decided explicitly.)
6. **Backfill scope**: active products only (`is_active=True`) or all rows including deactivated? (3,677 ASINs in current JSONs; the DB also holds deactivated history.)
7. **Dashboard copy**: "Lo más regalado este año" (`dashboard.html:157`) remains unsubstantiated even after curation. Change the label, or leave for a later change?
8. **Evaluation gate design**: 100 products ≈ 3% of the catalog; stratify by category (32 categories ⇒ ~3 per category) or by source? Who judges "suitable" — human labeling of the same 100 to measure agreement?

## 6. Risks / gotchas

- **Migration is untested by CI**: tests use `create_all` (`conftest.py:22`); the new Alembic migration must be applied/verified manually against a real (Postgres) DB, since CI never runs migrations.
- **Naive datetime convention**: new model columns must use `utcnow_naive` (`models.py:7-14`); the pinned `sqlmodel==0.0.27` breaks with TZ-aware datetimes (see requirements.txt header).
- **HTTP client dependency**: production requirements have `requests`, not `httpx`. The classification job is production infrastructure — either use `requests` (sync, fine for a bounded job, zero new deps) or add `httpx` to `requirements.txt`. Do not rely on the dev-only install.
- **Railway cron restart loop** (documented in git history, `f01c55d`): a ≥1h backfill may be killed/restarted; the job must be idempotent and resumable, and should log progress so a restart can continue.
- **Long-tail categories**: 32 categories with near-uniform sizes (~145-150 each) — no category-level allowlist shortcut exists; classification must be per-product.
- **Blog lists can empty out**: price-bucket posts (`max_price ≤ 10`, `blog_config.py:9-12`) paginate over filtered results (`services.py:198-210`); enforcement may leave a curated list with zero items, including the hero image fallback (`services.py:212-213`).
- **Sitemap/SEO**: category pages are emitted for every category (`main.py:119-127`) regardless of post-filter emptiness.
- **Provider claims unproven**: qwen3.6 strict `json_schema` support, 60 rpm/5-concurrent limits, latency, cost, and quality are all external claims. Nothing in this repo can confirm them; the ~100-product bounded evaluation is the gate before any commitment.
- **Python version drift**: system python is 3.14, CI is 3.13, worktree has no venv. Use the main repo's 3.13.5 venv (verified: 128 tests pass from the worktree) or create a worktree venv before running the suite.

## 7. Residual unknowns

- Actual NaN Builders API surface: exact model IDs available, response format stability, 429/retry semantics, whether strict `json_schema` is honored by qwen3.6 (and how gemma4 compares) — external, to be validated by the bounded evaluation.
- Classification quality from titles alone (no images, no prices): unknown until the evaluation runs.
- Production DB contents (row counts, deactivated share) — not observable from the repo; the JSONs suggest ~3.7k active ASINs.
- Whether a staging environment exists for shadow-mode observation, or shadow runs directly on production.
- Multi-source category history: not stored today (§2.2); if the fingerprint needs per-source categories, that is extra schema/scope this change must consciously include or exclude.

## 8. Ready for proposal

Yes. The direction is implementable as explored; approach A is recommended. The proposal should resolve (or explicitly defer) the open decisions in §5, and the spec should include the evaluation gate (§5.8) as a precondition for enabling enforcement.
