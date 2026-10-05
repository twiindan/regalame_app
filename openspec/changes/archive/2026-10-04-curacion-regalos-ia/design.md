# Design: AI-assisted gift catalog curation (`curacion-regalos-ia`)

## Technical Approach

Offline classification of catalog products into editorial states (`eligible` / `contextual` / `excluded` / `unknown`), persisted in an additive `editorial_decision` table, plus a centralized, mode-gated visibility predicate applied inside `search_products`' shared `filters` list **before** `count` (catalog.py:145). Shadow mode (`off`, the default) provably changes nothing; `enforce` activates only after a persisted evaluation-gate pass.

The work splits into four focused modules plus one migration:

1. **`models.py`** — `EditorialDecision` (single table, AI + manual-override fields) and `EditorialGateState` (single-row gate record).
2. **`curation.py`** — editorial policy + query-side logic: effective-mode resolution, the visibility SQL predicate, fingerprint computation, pending-product selection, decision persistence.
3. **`curation_provider.py`** — NaN Builders OpenAI-compatible adapter over the pinned production `requests` (2.32.5), with an injectable transport seam and strict local response validation.
4. **`jobs/classify_catalog.py`** and **`jobs/evaluate_curation.py`** — the classification job (mirroring `jobs/refresh_catalog.py`'s `main()` + `run()` shape) and the offline evaluation-gate harness.
5. **`catalog.py` / `main.py` / `templates/blog_post.html`** — predicate insertion, context-surface wiring, blog empty state.

The import pipeline (`scraper.py`, `catalog.import_from_json`, `jobs/refresh_catalog.py`) and wish lists are untouched; `import_from_json` (catalog.py:236-321) writes only `Product`/`ProductList`, so it cannot write editorial state by construction.

## Architecture Decisions

### Decision 1: Manual override representation — single table, nullable override fields

**Choice**: One row per product in `editorial_decision` holds BOTH the AI decision and the manual override as separate nullable column groups (`manual_state`, `manual_context`, `manual_reason`, `manual_updated_at` vs. AI-side `state`, `context`, `reason`, `model_id`, `policy_version`, `input_fingerprint`, `classified_at`). The **effective state** is defined in SQL as `func.coalesce(EditorialDecision.manual_state, EditorialDecision.state)`; likewise `coalesce(manual_context, context)`. Missing row or all-NULL states ⇒ `unknown`.

**Alternatives considered**: a sibling `manual_editorial_decision` table with join/priority logic.

**Rationale**: `coalesce` encodes the "manual always wins" rule directly in the single SQL expression used by every read path — no join, no priority resolution, no second query. The job's skip rule (`manual_state IS NOT NULL` ⇒ never re-requested) and the operator write path (set 4 columns) both become trivially auditable. A sibling table only adds a join and an ordering rule with zero benefit. The classifier job writes only the AI-side columns; it literally has no code path touching `manual_*`, and `import_from_json` touches neither.

### Decision 2: Table name, cardinality, migration, datetimes

**Choice**:
- Table `editorial_decision`, SQLModel class `EditorialDecision`, `product_id` unique + indexed FK to `product.id` (one row per product, upsert by `product_id`).
- New Alembic migration `down_revision = "9f1c7b2a4d3e"` (verified head: no other migration references it as `down_revision`; file `9f1c7b2a4d3e_add_product_tables.py`). Strictly additive: two `op.create_table` calls, nothing else.
- Naive-UTC datetimes via the existing `utcnow_naive` (models.py:7) and `default_factory=`; `sqlmodel==0.0.27` pin untouched.

**Alternatives considered**: piggy-backing columns onto `Product` (rejected in the proposal — couples the importer to curation and loses state on wholesale upserts).

**Rationale**: matches the proposal's verified migration chain and the repo's naive-datetime convention (an aware value round-trips back naive from a naive column and then compares unequal — see `utcnow_naive` docstring).

### Decision 3: Gate/coverage state — persisted single-row table

**Choice**: `editorial_gate_state` (class `EditorialGateState`), single row (PK conventionally `1`, upserted by the evaluation job): `gate_passed: bool`, `coverage_ratio: float`, `unknown_ratio: float`, `overall_agreement: float | None`, `excluded_leak_ratio: float | None`, `policy_version: str`, `model_id: str`, `evaluated_at`, `updated_at`. Effective mode resolution:

```python
def effective_filter_mode(session: Session) -> str:
    if EDITORIAL_FILTER_MODE != "enforce":   # module-level os.getenv("EDITORIAL_FILTER_MODE", "off")
        return "off"                          # no DB read at all in the default world
    gate = session.exec(select(EditorialGateState).limit(1)).first()
    if gate is None or not gate.gate_passed or gate.policy_version != EDITORIAL_POLICY_VERSION:
        return "off"
    return "enforce"
```

**Alternatives considered**: computing gate state live per request (extra aggregate queries on every surface); env-only gate (unauditable, not per spec — spec requires results *recorded*).

**Rationale**: one tiny SELECT per `search_products`/`list_categories` call, and only when the operator has configured `enforce` — the default `off` path performs zero extra queries and appends zero SQL, which is what makes the shadow guarantee structural (Decision 4). Requiring `gate.policy_version == EDITORIAL_POLICY_VERSION` prevents a stale gate pass from authorizing a new policy. Missing/failing row ⇒ effective `off` (spec: "Enforce without a passing gate behaves as off").

### Decision 4: Shadow byte-identical guarantee — structural proof + golden lock

**Choice**: two complementary, automated tests (strict TDD RED before implementation):

- **T1 — structural, self-contained (primary guarantee)**: with mode `off` and decision rows present (including `excluded`), capture every SQL statement executed by the request path via a SQLAlchemy `before_cursor_execute` listener on the test engine, and assert:
  1. no captured statement references `editorial_decision` or `editorial_gate_state` (in `off`, `effective_filter_mode` returns before any DB read, and no predicate is appended — so the executed SQL is literally the pre-change SQL);
  2. byte-equality of each surface's response body captured **with** decision rows vs. **after deleting** all decision rows from the same DB — proving the responses are independent of editorial data, hence identical to the behavior this change replaces.
- **T2 — golden lock (drift protection)**: checked-in baseline snapshots (`tests/baselines/editorial_off_<surface>.html`) of the shared surfaces — `/`, `/catalog`, `/catalog?category=…`, `/trends`, `/most-desired`, `/bestsellers`, `/ideas/{slug}`, `/blog/{slug}`, `/sitemap.xml` — rendered under `off` with decision rows present. A pytest flag `--editorial-update-baselines` (added to `tests/conftest.py`) regenerates them.

**Baseline capture and maintenance**: baselines are generated by running the suite with `--editorial-update-baselines` on the change branch while mode is `off`. This is sound because T1 proves the off-mode request path never reads editorial tables, so the captured bytes are produced by the unchanged pre-change query code. Baselines are committed and diff-reviewed; they are regenerated **only** when an intentional change to pre-change behavior lands in a separate review, never silently. This combination gives "byte-identical to what this change replaces" (T1, by construction) and "stays identical over time" (T2, by regression lock).

**Alternatives considered**: generating baselines from pre-change HEAD in a second worktree (heavier CI choreography, no additional guarantee over T1's data-independence proof); runtime response hashing (weaker, no diff to review).

### Decision 5: Fingerprint — exact inputs, JSON-canonical SHA-256, shared home

**Choice**: `compute_fingerprint(title_normalized: str, category: str, policy_version: str, model_id: str) -> str` in `curation.py`:

```python
def compute_fingerprint(title_normalized, category, policy_version, model_id):
    payload = json.dumps([title_normalized, category, policy_version, model_id], ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
```

- Inputs are exactly `Product.title_normalized` (already maintained by the importer, catalog.py:282/296), the last observed single `Product.category` (display name; last-write-wins per catalog.py:299-300 — multi-source history explicitly out of scope), `EDITORIAL_POLICY_VERSION` (module constant in `curation.py`, bumped only with a spec update + prompt change), and the configured `EDITORIAL_PROVIDER_MODEL`.
- `json.dumps` of a list makes the serialization delimiter-unambiguous (a JSON document cannot be parsed two ways), unlike a separator join where `\x1f` could theoretically survive normalization.
- Price, rank, `scraped_at`, `updated_at`, `is_active` are **not** inputs (spec scenarios).
- The function lives in `curation.py` and is used by both the job's persistence path (`apply_decision` stores it) and the staleness check (`pending_products` recomputes it per product and compares with the stored `input_fingerprint`), so job and check cannot drift.

**Alternatives considered**: SQL-side fingerprint computation (duplicates the hash in SQL dialects); naive `\x1f`-joined string (delimiter-ambiguity edge).

### Decision 6: Provider adapter — injectable seam, production `requests`, strict local validation

**Choice**: `curation_provider.py` with the same seam philosophy as `jobs/refresh_catalog.py`'s `scrape_fn`:

```python
Transport = Callable[[dict], dict]   # payload -> parsed JSON body

def classify_product(item: dict, *, transport: Transport | None = None, timeout: float = 30.0,
                     max_attempts: int = 2) -> ClassificationResult | None
def _post_chat_completions(payload: dict) -> dict   # production transport: requests.post(...)
def parse_provider_response(body: dict) -> ClassificationResult | None   # pure validation
```

- Production transport uses the pinned `requests==2.32.5` — `requests.post(f"{EDITORIAL_PROVIDER_BASE_URL}/chat/completions", headers={"Authorization": f"Bearer …"}, json=payload, timeout=…)`. Base URL (default `https://api.nan.builders/v1`), model (default `qwen3.6`), and API key come from module-level `os.getenv` (repo convention, cf. `email_utils.py`); tests inject `transport=` fakes so **CI makes zero network calls**.
- One product per request (the proposal's 60 rpm ⇒ ~61 min backfill math assumes this), with `response_format: {"type": "json_schema", "json_schema": DECISION_JSON_SCHEMA}` where `DECISION_JSON_SCHEMA` is a strict object schema with `state` enum `["eligible","contextual","excluded","unknown"]`, nullable `context`, non-empty `reason`. `unknown` is a first-class **valid** model outcome ("cannot determine gift suitability from title+category"), so it can be persisted with a current fingerprint — otherwise uncovered products would be re-requested on every cron run forever and coverage could never reach 100%.
- **Strict local validation regardless of provider behavior** (`parse_provider_response`): body shape (`choices[0].message.content` parses as a JSON object), `state` ∈ enum, `contextual` ⇒ non-empty `context` ∈ `EDITORIAL_CONTEXTS` (policy list), non-contextual ⇒ `context` normalized to `None`, `reason` non-empty. Any violation ⇒ `None` ⇒ failure-not-cached. Provider claims about `json_schema` support remain unproven (Decision 8 of the proposal); if the gate shows the provider rejects `response_format`, the fallback (plain JSON instructions + same local validation) is a `EDITORIAL_POLICY_VERSION` bump, re-gated.
- Bounded retries (`max_attempts`, default 2) per product; exhaustion ⇒ `None` for that product, work deferred to the next cron run.
- **No-network dry-run vs. shadow-run**: `dry_run=True` in `jobs/classify_catalog.run()` runs selection + reporting but never calls `classify_fn` and never writes (asserted by a RED test that injects a transport-recording fake and a session and asserts zero calls/writes). Shadow run (`dry_run=False`, mode `off`) makes real calls and persists decisions with zero public effect — `enforce` is a web-side config flag, never a job mode.

**Alternatives considered**: batching N products per request (fragile variable-length schemas, muddles per-product failure isolation and resumability); `httpx` (new production dependency — rejected by proposal).

### Decision 7: Job structure — mirror `refresh_catalog`, progress IS the decision table

**Choice**: `jobs/classify_catalog.py` with module docstring, `_parse_args(argv)`, `run(session, classify_fn=…, dry_run=False, limit=None, max_seconds=None, log=print) -> int`, `main(argv=None, session=None) -> int` (owned `Session(engine)` when `session is None`), `sys.exit(main())` guard — the exact shape of `jobs/refresh_catalog.py:103-175`. Properties:

- **Incremental**: `pending_products(session, policy_version=…, model_id=…)` returns only active (`is_active=True`) products with no decision row, a fingerprint mismatch, or no manual override (rows with `manual_state IS NOT NULL` are deliberately excluded — the job never spends provider calls whose result would be discarded; the override remains effective, satisfying "override wins over fresh AI output").
- **Resumable**: progress is the decision table itself — each product's decision is committed in batches (`EDITORIAL_JOB_COMMIT_EVERY`, default 25) and a restarted run re-queries pending, skipping everything with a current fingerprint. No separate checkpoint table. In-flight uncommitted work on a Railway cron kill is simply re-requested.
- **Idempotent**: upsert by unique `product_id`; a completed backfill re-run selects zero pending products ⇒ zero provider calls, zero writes (spec scenario).
- **Bounded**: sequential loop (concurrency 1 — the shipped default; the seam allows a pool later), rate limit via inter-request sleep targeting `EDITORIAL_JOB_RPM` (default 60), wall time `EDITORIAL_JOB_MAX_SECONDS` (default 3300) checked before each request, per-run cap `EDITORIAL_JOB_MAX_PRODUCTS` (default 500). Reaching any bound stops cleanly with exit 0 and a `stopped=reason` log line.
- **Logging**: per-batch progress lines `batch=k classified=n pending=m elapsed=s` (via the injectable `log`, default `print`) so Railway cron restarts are diagnosable.

**Alternatives considered**: ThreadPoolExecutor concurrency (unnecessary complexity until the gate proves latency requires it); a checkpoint table (redundant — the fingerprint check is the checkpoint).

### Decision 8: Centralized predicate — exact insertion point and mode gating

**Choice**: `curation.py` exposes the predicate factory; `search_products` (catalog.py:114) consumes it:

```python
# catalog.py — search_products, at the shared filters list (127-143)
    filters = [Product.is_active == True]
    ...existing term/category/source/price filters...
    visibility = editorial_visibility(session)          # None when effective mode == off

    if query.category_slug and visibility is not None and query.editorial_context == query.category_slug:
        # Context surface (/ideas/{slug}): the category filter MERGES with contextual visibility.
        filters.append(visibility.context_category(query.category_slug))   # appended before count (145)
    else:
        if query.category_slug:
            filters.append(Product.category_slug == query.category_slug)   # unchanged (130-131)
        if visibility is not None:
            filters.append(visibility.general())                            # appended before count (145)
```

with `CatalogQuery` gaining `editorial_context: Optional[str] = None` (catalog.py:81). The two predicates:

```python
# general surfaces (enforce): eligible only — no row ⇒ unknown ⇒ hidden (IN-subquery, mirroring the
# source filter pattern at catalog.py:133-137)
Product.id.in_(
    select(EditorialDecision.product_id).where(
        func.coalesce(EditorialDecision.manual_state, EditorialDecision.state) == "eligible")
)

# context surface /ideas/{slug} (enforce): eligible products of the category PLUS contextual products
# whose effective context matches the slug (excluded/unknown/no-row match neither branch)
or_(
    and_(Product.category_slug == slug, <general eligible subquery>),
    and_(func.coalesce(EditorialDecision.manual_state, EditorialDecision.state) == "contextual",
         func.coalesce(EditorialDecision.manual_context, EditorialDecision.context) == slug),
)
```

- **Mode gating**: `editorial_visibility(session)` returns `None` unless `effective_filter_mode(session) == "enforce"`; `None` ⇒ zero appended conditions ⇒ the executed SQL is byte-for-byte the pre-change SQL (Decision 4/T1).
- **Contextual inclusion**: only surfaces that explicitly set `editorial_context` get the context branch. Today that is exactly one route: `/ideas/{category_slug}` (main.py:413) passes `editorial_context=category_slug` through a new `_catalog_context` kwarg (main.py:239) into `CatalogQuery`. `/catalog?category=…`, blog lists (`services.get_blog_post_detail`, services.py:201-206), and the dashboard samples (main.py:213-215) stay general surfaces — `contextual` hidden there. Totals/pagination are correct on all 30 call sites because the predicate joins the shared `filters` list **before** `total` (catalog.py:145).
- **`list_categories` and the sitemap read the same predicate**: `list_categories` (catalog.py:181) gains a suppression branch computed by `visible_category_slugs(session) -> set[str] | None` in `curation.py` (None when off):

```sql
SELECT DISTINCT p.category_slug FROM product p WHERE p.is_active AND <general eligible subquery>
UNION
SELECT DISTINCT coalesce(d.manual_context, d.context)
FROM editorial_decision d JOIN product p ON p.id = d.product_id
WHERE p.is_active AND coalesce(d.manual_state, d.state) = 'contextual'
```

  `list_categories` then filters its grouped query to `category_slug IN visible` under `enforce`. The UNION (not a GROUP BY over `Product`) is required because a contextual product's context may differ from its own category — the grouped query would over-suppress. **`main.py`'s sitemap (92-145) needs NO code change**: it already renders `list_categories(session)` (main.py:119), so suppression propagates automatically.

**Alternatives considered**: post-query filtering (breaks totals/pagination ×30 — rejected in proposal); per-route predicates (duplicates logic; rejected).

### Decision 9: File/module layout

| File | Action | Responsibility |
|------|--------|----------------|
| `models.py` | Modify | Add `EditorialDecision`, `EditorialGateState` (after `ProductList`; naive datetimes via `utcnow_naive`) |
| `alembic/versions/<rev>_add_editorial_decision.py` | Create | Additive migration: `create_table("editorial_decision")`, `create_table("editorial_gate_state")`; `down_revision="9f1c7b2a4d3e"` |
| `curation.py` | Create | Policy constants (`EDITORIAL_STATES`, `EDITORIAL_POLICY_VERSION`, `EDITORIAL_CONTEXTS`), env reads, `effective_filter_mode`, `editorial_visibility` + predicate builders, `compute_fingerprint`, `pending_products`, `apply_decision`, `visible_category_slugs` |
| `curation_provider.py` | Create | Provider adapter: `classify_product`, `_post_chat_completions`, `parse_provider_response`, `DECISION_JSON_SCHEMA`, policy prompt constant |
| `jobs/classify_catalog.py` | Create | Classification job: `_parse_args`, `run`, `main`; bounds, rate, batching, progress logs |
| `jobs/evaluate_curation.py` | Create | Gate harness: stratified `sample_products`, `evaluate`, label-template output, `EditorialGateState` upsert |
| `catalog.py` | Modify | `search_products` predicate insertion + `CatalogQuery.editorial_context`; `list_categories` suppression branch |
| `main.py` | Modify | `/ideas/{slug}` route + `_catalog_context` gain `editorial_context` pass-through (sitemap untouched) |
| `templates/blog_post.html` | Modify | Graceful empty state when the filtered product list is empty (hero fallback already guards on `products` truthiness, services.py:212-213) |
| `tests/conftest.py` | Modify | `--editorial-update-baselines` option; decision-seeding helper fixture |
| `tests/test_curation.py` | Create | Model semantics, fingerprint rules, pending selection, apply/upsert, manual-wins, importer-neutral |
| `tests/test_curation_provider.py` | Create | Transport-fake adapter, schema validation, invalid-response ⇒ None, retries bounded |
| `tests/test_classify_catalog.py` | Create | Incremental/resumable/idempotent/bounded, failure-not-cached, dry-run zero-call/zero-write, active-only scope |
| `tests/test_editorial_filtering.py` | Create | Modes, visibility, totals/pagination, contextual routing, category/sitemap suppression, blog empty state, T1+T2 shadow guarantees |
| `tests/test_curation_gate.py` | Create | Sample stratification, metric math, pass/fail scenarios per spec, single-row upsert |
| `tests/baselines/` | Create | Golden off-mode response snapshots (T2) |

Focused modules: `curation.py` = domain + query logic; `curation_provider.py` = I/O only; jobs = orchestration only; `catalog.py` change limited to consuming `curation`.

## Data Flow

```
                    ┌──────────────────── off-line (Railway cron) ────────────────────┐
                    │                                                                  │
  Amazon lists ──► scraper.py ──► jobs/refresh_catalog.py ──► Product / ProductList   │   (UNTOUCHED;
                    │                                          ▲                      │    never writes
                    │                                          └── import_from_json   │    editorial state)
                    │                                                                 │
  ops (labels) ──► jobs/evaluate_curation.py ── sample/evaluate ──► editorial_gate_state (1 row)
                    │                                                        │
  provider (NaN    └─► jobs/classify_catalog.py ── curation_provider        │
  Builders, HTTPS)         │   classify_product(title, category)  │         │
                    │      │  valid ──► apply_decision ──► editorial_decision │
                    │      └─ invalid/failure ──► NOTHING WRITTEN             │
                    └──────────────────────────────────────────────────────────┘

                    ┌──────────────── request path (web) ────────────────────────┐
  routes (main.py, services.py) ──► search_products(session, CatalogQuery)     │
                    │       └─ editorial_visibility(session)                    │
                    │            ├─ configured != enforce ──► None (no SQL added, no DB read)
                    │            └─ enforce ──► read editorial_gate_state ──► predicate into
                    │                 shared filters list BEFORE count (catalog.py:145)
                    │                 ├─ general surface: eligible only
                    │                 └─ /ideas/{slug}: eligible of category ∨ contextual(context=slug)
                    └──► list_categories ──► visible_category_slugs ──► nav + sitemap (auto)
```

Manual overrides: written out-of-band by operators against the model (4 `manual_*` columns); read paths apply `coalesce(manual, ai)`; the classifier skips manual rows; imports never touch the row.

## Interfaces / Contracts

```python
# curation.py
EDITORIAL_POLICY_VERSION: str            # "1"; bump = prompt/policy change + spec update
EDITORIAL_FILTER_MODE: str               # os.getenv("EDITORIAL_FILTER_MODE", "off")
EDITORIAL_CONTEXTS: frozenset[str]       # closed policy vocabulary for contextual products

def effective_filter_mode(session: Session) -> str: ...
def compute_fingerprint(title_normalized: str, category: str,
                        policy_version: str, model_id: str) -> str: ...
def pending_products(session: Session, *, policy_version: str, model_id: str,
                     limit: int | None = None) -> list[Product]: ...
def apply_decision(session: Session, product: Product, result: ClassificationResult, *,
                   model_id: str, policy_version: str) -> EditorialDecision: ...
def visible_category_slugs(session: Session) -> set[str] | None: ...   # None when off

class _EditorialVisibility:             # returned only under enforce
    def general(self) -> ColumnElement[bool]: ...
    def context_category(self, slug: str) -> ColumnElement[bool]: ...
def editorial_visibility(session: Session) -> _EditorialVisibility | None: ...

# curation_provider.py
@dataclass(frozen=True)
class ClassificationResult:
    state: str; context: str | None; reason: str

Transport = Callable[[dict], dict]
def classify_product(item: dict, *, transport: Transport | None = None,
                     timeout: float = 30.0, max_attempts: int = 2,
                     base_url: str | None = None, model: str | None = None,
                     api_key: str | None = None) -> ClassificationResult | None: ...
def parse_provider_response(body: dict) -> ClassificationResult | None: ...

# jobs/classify_catalog.py
def run(session: Session, classify_fn=curation_provider.classify_product, *,
        dry_run: bool = False, limit: int | None = None,
        max_seconds: int | None = None, log=print) -> int: ...
def main(argv: list[str] | None = None, session: Session | None = None) -> int: ...

# jobs/evaluate_curation.py
def sample_products(session: Session, *, total: int = 100) -> list[Product]: ...
def evaluate(session: Session, labels_path: str) -> GateReport: ...
def run(session: Session, labels_path: str | None = None,
        sample_out: str | None = None, log=print) -> int: ...
def main(argv: list[str] | None = None, session: Session | None = None) -> int: ...

# catalog.py (modified)
@dataclass class CatalogQuery: ...; editorial_context: Optional[str] = None
def search_products(session: Session, query: CatalogQuery) -> CatalogResult: ...  # predicate before count
def list_categories(session: Session) -> list[tuple[str, str]]: ...               # suppression branch

# models.py (added)
class EditorialDecision(SQLModel, table=True): ...      # __tablename__ = "editorial_decision"
class EditorialGateState(SQLModel, table=True): ...     # __tablename__ = "editorial_gate_state"
```

Error handling summary: provider transport/timeout/invalid ⇒ `None` ⇒ nothing written (failure-not-cached holds by construction — there is no code path writing a decision without a validated `ClassificationResult`); bounded retries then defer; per-batch commits bound blast radius (failed batch rolls back that batch only, run continues); job exit 0 on clean stop (including bound reached), 1 on fatal (DB/connectivity at startup); gate job exits 1 on malformed or partially-filled labels file without writing the gate row.

## Testing Strategy

Strict TDD (`strict_tdd: true`): every behavior below is a RED test before its production change; runner `python -m pytest -q --ignore=tests/test_e2e.py` (baseline: 128 passing; worktree needs the venv bootstrapped from `requirements-dev.txt`).

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | Fingerprint rules (price/rank/scraped_at invariance; title/category/policy/model sensitivity; JSON-canonical determinism) | Pure-function tests on `compute_fingerprint` |
| Unit | Provider validation (valid body; each invalid shape ⇒ None; contextual-without-context ⇒ None; enum enforcement; retry bound) | Fake `transport` callables; zero network |
| Unit | Gate metric math (spec scenarios: 92% pass, 87% fail, leak 8% fail, coverage 97% fail, unknown 14% pass-with-flag) | Seeded session + labels file fixture |
| Unit | Effective-mode resolution (default off; configured-enforce + missing/failing/stale-policy gate row ⇒ off) | Seeded `EditorialGateState`, monkeypatched `EDITORIAL_FILTER_MODE` |
| Integration | Job: incremental, resumable (interrupt mid-run, restart), idempotent (re-run ⇒ zero calls), bounded (rate/wall/limit with recorded timings), active-only scope, dry-run zero-call/zero-write, failure-not-cached (transport error ⇒ no row; prior decision retained on stale-reclass failure) | Fake `classify_fn` recording calls; in-memory session |
| Integration | Filtering: totals/pagination under `enforce` (filtered totals, page 2 tail, no gaps); contextual visible only under matching context; excluded/unknown/no-row hidden everywhere; dashboard/catalog/trends/most-desired/bestsellers/ideas/blog all filter | TestClient + `catalog_seed` + decision fixtures |
| Integration | Suppression: zero-visible categories dropped from `list_categories` (hence sitemap) under `enforce`; retained with ≥1 visible; unchanged under `off` | TestClient `/sitemap.xml` + direct `list_categories` |
| Integration | Blog: empty filtered list renders empty state; hero fallback not derived from empty list; hero from first visible product otherwise | TestClient `/blog/{slug}` |
| Integration | Manual override wins over fresh AI output and survives re-runs; importer writes no editorial state (run `import_from_json`, assert decision table unchanged) | Session-level tests |
| Integration (T1) | Shadow structural proof: SQL capture shows no editorial-table reference under `off`; response bytes independent of decision-row presence | `before_cursor_execute` listener on the test engine |
| Regression (T2) | Golden baselines: off-mode surfaces match `tests/baselines/` byte-for-byte | `--editorial-update-baselines` regeneration flow |
| Manual | Migration on Postgres (CI never runs Alembic — `conftest.py` uses `create_all`) | Runbook below |

**Migration manual verification runbook (pre-deploy gate)**: on a Postgres snapshot of production: `alembic upgrade head` → assert `editorial_decision` and `editorial_gate_state` exist and `\d+ product`, `\d+ productlist` are unchanged → exercise a read route → `alembic downgrade -1` → assert tables dropped, data intact → `alembic upgrade head` again. Record output in the deploy PR.

## Threat Matrix

Applicability-driven (per `references/threat-matrix.md`). This change adds no routing, shell-command composition, VCS/PR automation, or executable-file classification inside the product. The one process-integration surface is the new Railway-cron CLI job (network + DB writes outside the web process).

| Boundary | Applicability | Reason / Design response | Planned RED tests |
|----------|--------------|--------------------------|-------------------|
| Documentation-like paths | N/A | No executable markdown/docs handling introduced | — |
| Git repository selection | N/A | No git automation in the change | — |
| Commit state | N/A | No git operations | — |
| Push state | N/A | No git operations | — |
| PR commands | N/A | No PR automation | — |
| Process integration (cron job: `python -m jobs.classify_catalog`) | **Applicable** | New scheduled process performing provider network calls and DB writes. Safe behavior: dry-run writes nothing; shadow persists only validated decisions; bounds stop cleanly; CI never reaches the network (transport always injected in tests). Failure behavior: transport/invalid ⇒ no write; fatal DB error ⇒ exit 1 | Dry-run zero-call/zero-write (recording fake); bounds test with recorded call timings; failure-not-cached tests (Decision 4 of spec tests, above) |

## Migration / Rollout

No data migration of existing rows is needed — the schema change is purely additive and starts empty.

Rollout phases: (1) merge with `EDITORIAL_FILTER_MODE` unset ⇒ `off`; deploy; T1/T2 prove zero public change. (2) Run `jobs/classify_catalog.py` in dry-run, then shadow, via Railway cron until backfill coverage of active products is 100%. (3) Generate the stratified sample, human-label it, run `jobs/evaluate_curation.py`; gate row records the verdict. (4) Only after `gate_passed=true` with 100% coverage, set `EDITORIAL_FILTER_MODE=enforce`.

Rollback: (1) primary — unset/flip `EDITORIAL_FILTER_MODE` to `off` (or `DELETE FROM editorial_gate_state`): surfaces revert instantly, persisted decisions become inert; no code revert. (2) job misbehaves — remove the cron entry. (3) bad policy — bump `EDITORIAL_POLICY_VERSION`: all AI fingerprints go stale, next runs reclassify, manual overrides keep winning. (4) `alembic downgrade -1` available and verified per runbook, but never required for behavior rollback.

## Open Questions

- [ ] **Initial `EDITORIAL_CONTEXTS` vocabulary**: recommended v1 constraint — the classifier may only emit a context equal to the product's own `category_slug` (guarantees every contextual product has a live `/ideas/{slug}` surface and zero new routes); widening to a curated superset (`bebe`, `mascotas`, …) is a policy-version bump once we see gate data. Needs product sign-off at apply time.
- [ ] **Provider claim verification** (strict `json_schema`, 60 rpm, latency): resolved empirically by the gate; if `response_format` is rejected, the documented fallback (plain JSON instructions + unchanged strict local validation) requires a policy bump — decide then, not now.
- [ ] **Residual-`unknown` follow-up policy**: if the SHOULD threshold (≤10%) is exceeded after backfill, decide between prompt iteration (policy bump) and accepting the flag; gate currently only warns.
