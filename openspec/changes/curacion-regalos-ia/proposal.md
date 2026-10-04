# Proposal: AI-assisted gift catalog curation (`curacion-regalos-ia`)

Source of truth: `openspec/changes/curacion-regalos-ia/exploration.md` (verified against worktree commit `33754d3`). This proposal adopts the exploration's recommended **Approach A** and resolves the §5 open decisions with the orchestrator defaults recorded below (each is user-adjustable later).

## Intent

The public catalog is a raw, uncurated mirror of three Amazon.es ranking lists: 3,677 distinct ASINs across 32 categories, including obvious non-gift material (office supplies, DIY tools, "Amazon Renewed", "Climate Pledge Friendly" — real observed categories). The UI presents all of it as gift recommendations. There is no editorial layer of any kind: what Amazon lists is what users see.

This change adds an **offline, AI-assisted gift-suitability classification** of catalog products and a **centralized editorial filter** that applies those decisions across all public product surfaces — keeping the commercial import pipeline (`scraper.py`, `catalog.import_from_json`) and user wish lists (`Wish`) untouched.

## Decisions (resolving exploration §5 — user-adjustable)

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | `contextual` = hidden from general surfaces; visible only under a matching context route/filter (e.g. baby, pets, platform). Not a general-surface badge. | Keeps general surfaces strictly gift-focused while preserving relevance where the context applies. |
| 2 | `unknown` (unclassified/invalid) is NOT promoted: never shown on general surfaces; hidden until a valid classification exists. | "Not promoted" must not silently equal "treated as eligible"; unresolved items carry no evidence of suitability. |
| 3 | Filter modes: `off` (shadow, **default**) and `enforce`. In `enforce`: general surfaces show only `eligible`; `contextual` appears only under its matching context; `excluded` and `unknown` are hidden. Enforcement is enabled only after the evaluation gate passes and the backfill completes. | Shadow mode proves zero public impact before any behavior change; whitelist semantics only once coverage and quality are proven. |
| 4 | Empty categories: suppress categories with zero visible products from navigation (`list_categories`) and the sitemap. | Empty `/ideas/{slug}` pages and dead sitemap entries damage SEO/UX. |
| 5 | Fingerprint inputs: `title_normalized` + last observed single `category` + policy/schema version + model id. Multi-source category history is explicitly OUT of scope (documented limitation, revisit later). | `Product.category` is last-write-wins today (`catalog.py:299-300`); per-source history would add schema and scope not yet justified. |
| 6 | Backfill scope: active products only (`is_active=True`). | Deactivated products are not renderable; classifying them wastes cost and time. |
| 7 | Dashboard copy "Lo más regalado este año" (`templates/dashboard.html:157`): OUT of scope, recorded as follow-up (it remains unsubstantiated by the filter). | Copy is a product decision independent of curation; bundling it weakens review focus. |
| 8 | Evaluation gate: bounded offline evaluation on ~100 products stratified across categories with human-labeled expected outcomes; MUST pass before `enforce` is enabled. No user data stored or sent to the provider. | All provider claims (strict `json_schema`, rate limits, quality) are unproven from this repo; the gate is the commitment point. |

Additional recorded decisions:

- **Provider**: NaN Builders, OpenAI-compatible base URL `https://api.nan.builders/v1`; API key via environment variable; model configurable, initial candidate `qwen3.6`, alternative `gemma4`. All provider claims remain unproven and gated by Decision 8.
- **HTTP client**: the existing production dependency `requests`; no new production deps (`httpx` stays dev-only).
- **Datetimes**: the new model keeps the naive-datetime convention (`utcnow_naive`, `sqlmodel==0.0.27` pin).
- **Migration**: new Alembic migration with `down_revision = "9f1c7b2a4d3e"` (verified head).
- **Job model**: classification is a separate job from the scraper; incremental, resumable, idempotent, bounded in concurrency, request rate, and wall time.
- **Failure semantics**: transport/timeout/invalid-response failures are NEVER cached as editorial exclusions.

## Scope

### In Scope

1. **Editorial decision schema** (additive): new table keyed by product holding state (`eligible` / `contextual` / `excluded` / `unknown`), context (required for `contextual`), reason, model id, policy/schema version, input fingerprint, naive-UTC timestamps; plus manual-override records that always win over AI decisions (data-level mechanism; no admin UI). Alembic migration chained to head `9f1c7b2a4d3e`.
2. **Offline classification job** (`jobs/classify_catalog.py`): CLI `main()` + `run()` seam with injectable provider (pattern of `jobs/refresh_catalog.py`); NaN Builders OpenAI-compatible API via `requests`; configurable model and env-var API key; fingerprint-based reclassification triggers; incremental, resumable, idempotent; bounded concurrency/rate/wall-time; no-network dry-run mode and real-calls shadow run mode (persists decisions, no public effect).
3. **Backfill**: active products only (`is_active=True`); resumable across Railway cron restarts (~61 min lower bound at 60 rpm for 3,677 ASINs).
4. **Centralized editorial filter**: one predicate added to `search_products`' shared `filters` list **before count** (`catalog.py:127-143`), correcting totals/pagination for all 30 call sites at once; mode-gated (`off`/`enforce`).
5. **Leak fixes**: `list_categories` (`catalog.py:181-189`) and the sitemap (`main.py:119-127`) suppress zero-visible-product categories under `enforce`; graceful empty state for blog product lists (`services.py:198-213`), including the hero image fallback.
6. **Evaluation gate**: stratified ~100-product offline evaluation harness with human-labeled expected outcomes; results recorded before `enforce` may be enabled.
7. **Tests** (strict TDD): classification job, fingerprints, failure-not-cached, idempotency/resumability, filter modes, contextual visibility, category/sitemap suppression, blog empty states.

### Out of Scope

- Commercial import pipeline: `scraper.py`, `catalog.import_from_json` (`catalog.py:236-321`), `deactivate_absent_products` — untouched (the importer never writes editorial state, by construction).
- Wish lists: `Wish` model (`models.py:82-95`) and routes (`main.py:784-865`) — untouched.
- Multi-source category history storage — documented limitation (Decision 5).
- Dashboard copy "Lo más regalado este año" — follow-up change (Decision 7).
- Request-time AI calls; multimodal classification (inputs are title + category only).
- New production dependencies (no `httpx`); no admin UI for manual overrides.
- Re-ranking or ordering changes beyond the filter predicate.

## Capabilities

> Contract for `sdd-spec`. `openspec/specs/` is empty today — every capability below is new.

### New Capabilities

- `product-editorial-classification`: Offline AI classification of catalog products into editorial states (`eligible`/`contextual`/`excluded`/`unknown`), covering the additive decision schema with manual overrides, input-fingerprint invalidation, the resumable bounded classification job with failure-not-cached semantics, provider integration, and the human-labeled evaluation gate that preconditions enforcement.
- `catalog-editorial-filtering`: Centralized, mode-gated enforcement of editorial decisions on public product surfaces — a single predicate in `search_products` before count, `contextual` visibility only under a matching context, zero-visible category suppression in `list_categories` and the sitemap, blog empty-state handling, and the shadow (`off`) zero-behavior-change guarantee.

### Modified Capabilities

None — no existing specs in `openspec/specs/`.

## Approach

Adopts exploration **Approach A: separate editorial-decision table + centralized query filter.**

- **Additive schema**: `import_from_json` only writes `Product`/`ProductList` (`catalog.py:236-321`), so an editorial table it never touches is decoupled from the import pipeline by construction. `ProductList` rows and import health metrics are never modified by curation.
- **Centralized filter**: `search_products` builds one `filters` list before `count` (`catalog.py:127-145`); adding the editorial predicate there fixes totals, pagination, and all 30 call sites (dashboard samples, `/catalog`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, blog lists) in one place.
- **Why not the alternatives**: B (columns on `Product`) couples the importer to curation and loses editorial state on wholesale upserts; C (post-query filtering) breaks totals/pagination and duplicates logic ×30; D (filter at ingestion) merges two jobs, makes import health depend on an LLM, and prevents retroactive re-filtering on policy change.
- **Modes**: `off` (shadow, default — the job may run and persist decisions; public behavior identical to today) and `enforce` (predicate active; contextual routing active). The enforcement flag flips only after gate pass + completed backfill (Decision 3).
- **Config**: plain `os.getenv` at module level (repo convention): provider base URL, API key, model id, filter mode, job bounds (rate/concurrency/wall time).

## Affected Areas / Surfaces

| Area | Impact | Description |
|------|--------|-------------|
| `models.py` | New | Editorial decision model + manual-override representation (naive datetimes via `utcnow_naive`) |
| `alembic/versions/` | New | Additive migration, `down_revision="9f1c7b2a4d3e"` |
| `catalog.py` (`search_products`, `:114-178`) | Modified | Editorial predicate in the shared `filters` list before `count`; mode-gated |
| `catalog.py` (`list_categories`, `:181-189`) | Modified | Suppress zero-visible categories under `enforce` |
| `main.py` (sitemap, `:119-127`) | Modified | Same category suppression in the sitemap |
| `main.py` routes (`/catalog`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, dashboard) | Modified (indirect) | No route code change required; behavior changes via the centralized predicate |
| `services.py` (`:185-215`) | Modified | Blog product lists under filtering; graceful empty state + hero image fallback |
| `jobs/classify_catalog.py` | New | Classification job (CLI + injectable seam + dry-run) |
| `main.py` / config (`os.getenv` sites) | Modified | New env vars for provider, model, mode, bounds |
| `tests/` | New/Modified | Coverage per Testing Strategy |
| `scraper.py`, `catalog.import_from_json`, `Wish` routes | Untouched | Import pipeline and wish lists preserved |

## Data / Schema Changes

- New table `editorial_decisions` (final name in design): `product_id` (unique FK), `state` (`eligible`/`contextual`/`excluded`/`unknown`), `context` (nullable; required when `state='contextual'`), `reason`, `model_id`, `policy_version`, `input_fingerprint`, naive-UTC `classified_at` / `created_at` / `updated_at`.
- Manual-override representation (e.g. `is_manual` flag on the decision row or a sibling table — design decides) that always wins over AI output; the importer cannot write it.
- Fingerprint = hash of `title_normalized` + last observed single `category` + policy/schema version + model id (Decision 5); a changed fingerprint marks the row stale and reclassifies on the next job run.
- No changes to `Product`, `ProductList`, or any existing table; the migration is strictly additive.

## Job / Deployment Changes

- New job `jobs/classify_catalog.py` runs out-of-band via Railway cron; deployment stays web-only (`Procfile` unchanged).
- Job properties: incremental (only pending/stale fingerprints), resumable (missing row = pending), idempotent, bounded concurrency/requests/wall-time — required by the Railway cron restart loop documented in git history (`f01c55d`).
- Modes: no-network dry-run (unit-testable); shadow run (real provider calls, persists decisions, zero public effect); `enforce` is a config flag, not a job mode.
- New env vars (repo `os.getenv` convention): provider API key, base URL (default `https://api.nan.builders/v1`), model id, filter mode (`off`/`enforce`), job bounds.

## Impact on catalog pipeline & affiliate links (config rule)

- **Import pipeline**: untouched; import health metrics (`refresh_catalog.baseline_counts`) count `ProductList` rows, not filtered results, so editorial filtering cannot corrupt them. Curation never deletes products or `ProductList` rows.
- **Affiliate links**: link generation logic is untouched; fewer affiliate impressions are expected once `excluded`/`unknown` items are hidden under `enforce` — an accepted tradeoff of curation, measured via success criteria.

## Testing Strategy

- Strict TDD (`strict_tdd: true`); runner `python -m pytest -q --ignore=tests/test_e2e.py` (baseline: 128 passing via the main repo's Python 3.13.5 venv; the worktree has no venv).
- **Job**: injectable fake provider; fingerprint invalidation; failure-not-cached (transport error ⇒ no decision row); idempotency/resumability across restarts; bounded-run behavior; dry-run makes zero calls and zero writes.
- **Filtering**: `off` = behavior-identical responses; `enforce` totals/pagination correctness through `search_products`; `contextual` only under matching context; `excluded`/`unknown` hidden; empty-category suppression in `list_categories` + sitemap; blog empty state.
- **Migration**: CI never runs Alembic (`conftest.py` uses `create_all`); the migration is verified manually against Postgres before deploy (runbook step).

## Rollback Plan

1. **Primary rollback = config flip**: set the filter mode back to `off` → public surfaces return to pre-change behavior immediately; persisted decisions become inert. No code revert needed.
2. If the job misbehaves (cost/quality/rate): remove the cron entry; persisted decisions are harmless while `off`.
3. If a bad policy version was classified: bump the policy version → all fingerprints go stale → re-run the job; reclassification replaces decisions, manual overrides always win.
4. Schema is additive; `alembic downgrade` of the new migration is available but not required for behavior rollback — verify the downgrade on Postgres before relying on it.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Migration untested by CI (tests use `create_all`) | Medium | Manual Postgres verification pre-deploy; keep the migration trivially additive |
| Provider claims unproven (strict `json_schema`, 60 rpm / 5 concurrent, latency, quality) | Medium | Decision 8 gate blocks `enforce`; `gemma4` fallback; model id is config, not code |
| Railway cron restart loop kills a ~1h backfill | Medium | Idempotent + resumable job; progress logging; per-batch commits |
| Naive-datetime regression via the new model | Low | Follow the `utcnow_naive` convention; keep the `sqlmodel==0.0.27` pin |
| Blog/SEO lists empty under `enforce` | Medium | Graceful empty states; Decision 4 suppresses empty categories from nav/sitemap |
| `enforce` enabled before backfill completes empties general surfaces | Low | Decision 3: enforcement requires completed backfill + gate pass |
| Provider outage pollutes editorial state | Low | Failure-not-cached rule: no decision row on transport/timeout/invalid response |
| Affiliate revenue dip from hiding items | Medium | Accepted intent of the change; shadow metrics first, then measure post-enforce |

## Success Criteria

- [ ] Shadow mode (`off`) deployed with zero public behavior change; full suite green (`python -m pytest -q --ignore=tests/test_e2e.py`).
- [ ] 100% of active products (`is_active=True`) hold a classification decision after backfill; residual `unknown` share below the threshold fixed in spec.
- [ ] Evaluation gate passed: on ~100 stratified, human-labeled products, AI decisions agree with labels at the threshold fixed in spec, including zero human-labeled `excluded` items visible on general surfaces.
- [ ] In `enforce`: general surfaces show only `eligible`; `contextual` appears only under its matching context; `excluded`/`unknown` hidden.
- [ ] `list_categories` and the sitemap contain no category with zero visible products.
- [ ] Provider/transport failure during classification leaves catalog and decisions unchanged (failure-not-cached verified by test).
- [ ] Import pipeline untouched: import health metrics and `ProductList` behavior unchanged (existing tests green without semantic modification).
- [ ] Migration applied and verified on Postgres with `down_revision = "9f1c7b2a4d3e"`.
