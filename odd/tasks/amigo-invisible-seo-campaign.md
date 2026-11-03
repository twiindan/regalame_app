# Christmas "amigo invisible" SEO campaign (roadmap item 4 + campaign content)

Roadmap item 4 of the persisted roadmap `seo/next-improvements-roadmap`
(Engram #932) — "measured Search Console full property + page-query baseline" —
extended with the Christmas campaign content work the user requested on
2026-11-02. Design spec:
`docs/superpowers/specs/2026-11-02-amigo-invisible-seo-campaign-design.md`.
Implementation plan:
`docs/superpowers/plans/2026-11-02-amigo-invisible-seo-campaign.md`.
This is the only ODD planning artifact for this feature.

## Objective, problem, and why

Seasonal demand for "amigo invisible" spikes mid-November to December. Head
terms are held by large media listicles and are not winnable. The app's
winnable surfaces are tool-intent queries (`/amigo-invisible`), long-tail
audience/price queries, and informational queries. GSC was configured with
real data but no API tooling exists in the repo
(`requirements-search-console.txt` is pinned but unused). Data must drive
which pages get tuned and which content ships. Timing is the constraint:
content published after early November is unlikely to rank within this
campaign.

## Product decisions made by the user (2026-11-02)

- **Approach A (chosen):** repeatable GSC CLI tool in the repo
  (`tools/gsc_report.py`), over manual CSV exports (B) or external keyword
  research only (C).
- **Scope:** full campaign, sequenced — GSC tool -> baseline report ->
  user checkpoint -> on-page -> internal linking -> new content.
- **Credentials:** user has none yet and asked to be guided (~10 min GCP
  setup). Service-account-first design (see spec; OAuth refresh tokens in
  testing mode expire after 7 days, per roadmap #932 notes).

## Authorized scope and boundary

- Authorized: local implementation, strict TDD, tests, edits to
  `main.py`/templates/`blog_config.py`/`blog` config surface,
  `tools/gsc_report.py` + its tests, `.gitignore` additions, docs, work-unit
  commits on `feature/amigo-invisible-seo-campaign` (base `main` @ `917b4e7`),
  ODD doc + design spec.
- Not authorized: push, PR, merge (user-owned), production dependency
  changes (GSC deps stay in `requirements-search-console.txt`, local CLI
  only), committing any credential/token file, JSON-LD/canonical/sitemap
  policy rework beyond the FAQ-coverage check.
- No Node/bundler; keep Jinja2 + HTMX.
- UI copy: neutral Spanish. Technical docs: English.
- Untracked `sample.json` / `sample.curacion-worktree.json` are not touched.
- The `regalos-navidad-mas-deseados` organizer-aside exclusion stays.
- Audience posts require human review of the rendered product list before
  publish (same pattern as the 27-ASIN christmas guide).

## Task checklist and acceptance

### T1 — Credential setup + config plumbing

- `tools/gsc_report.py` auth layer: service account JSON at
  `tools/gsc_service_account.json` (gitignored), optional `GSC_SITE_URL`
  env override; documented OAuth fallback. Setup guide committed (docs).
- Acceptance: no secret paths tracked in git; auth errors produce actionable
  messages; unit-tested with fake credentials/transport.

### T2 — GSC client (fetch layer)

- `searchanalytics.query`: dimensions `[query, page]`, last N days
  (default 90), country `es`, paginated to row limit cap; exponential
  backoff on quota errors; explicit empty-data handling.
- Acceptance: RED -> GREEN with a fake transport (fixtures, no network);
  pagination and backoff covered by tests.

### T3 — Report builders (pure) + markdown output

- Pure functions over fetched rows: (V1) top seasonal queries by
  impressions; (V2) opportunities position 5-20; (V3) low CTR at good
  position (title/meta rework candidates); (V4) per-URL aggregate. Markdown
  emitter with explicit "no data" messages; thresholds configurable via CLI
  flags.
- Acceptance: RED -> GREEN on fixtures covering each view, edge cases
  (empty rows, single row, ties); pure layer has no I/O.

### T4 — Baseline run + data checkpoint (with user)

- Run the report against the real property; review findings with the user;
  record the chosen on-page/content targets in this document.
- Acceptance: baseline report artifact exists (gitignored or pasted into
  this doc without query PII concerns — queries are public search terms);
  targets listed below.

### T5 — On-page tuning driven by T4 (checkpoint output)

- Retune title/description/H1 of `/amigo-invisible` (and home only if the
  data warrants) toward the tool-intent queries observed in GSC; verify FAQ
  coverage of the landing against real queries.
- Acceptance: template tests assert new title/meta; existing
  `test_seo_landings.py` suite stays green; no behavior change elsewhere.

### T6 — Internal linking pass

- Blog posts <-> `/amigo-invisible` <-> related `/ideas/{slug}`; home ->
  christmas post; respect the christmas-guide aside exclusion.
- Acceptance: template tests assert the links; sitemap/robots untouched.

### T7 — Informational posts (2-3, text-only)

- Blog entries without products ("cómo organizar", "reglas", "frases");
  exact titles chosen from T4 data; graceful no-products rendering.
- Acceptance: `200`, single H1, canonical, in sitemap; empty-product
  rendering tested.

### T8 — Curated audience posts (1-2)

- "Compañeros de trabajo" / "niños" via existing `blog_config` criteria
  (multi-category + limit); human review of the rendered list with the user
  before declaring done.
- Acceptance: same as T7 plus user sign-off on the product selection.

### T9 — December re-measure (manual, not code)

- Re-run report first week of December; compare against baseline for the
  target queries; record outcome in this document.

## T4 targets (recorded 2026-11-03, confirmed by the user)

Baseline: `tools/reports/gsc-baseline-2026-11-03.md` (sc-domain property,
country `esp`, 2026-08-05..2026-11-03). The site's search presence is
brand-only and near zero (~100 impressions, 6 clicks in 90 days; in Spain
only the home appears: 32 impressions, 0 clicks, avg position 26.44;
`/amigo-invisible` and the blog have zero Spain impressions). GSC has no
page-level signal to act on, so the plan's defaults hold:

- **`/amigo-invisible` (Plan task 8):** keep the current title, meta
  description and H1 verbatim. Additions only: visible FAQ section (3
  Q&As) with matching FAQPage JSON-LD, and an `/ideas` anchor in the ideas
  section.
- **Informational posts (Plan task 11):** titles/slug/copy as written in
  the plan — "Cómo organizar un amigo invisible paso a paso",
  "Reglas del amigo invisible: cómo se juega", "Frases para el amigo
  invisible: para el grupo, el papelito y el regalo".
- **Audience posts (Plan task 13):** "Amigo invisible para compañeros de
  trabajo: ideas que aciertan" (multi-category, max_price 15, limit 20) and
  "Amigo invisible para niños: regalos que aciertan" (Juguetes y juegos +
  Libros, limit 20), subject to the human review checkpoint.
- **December comparison:** judge movement against this baseline snapshot;
  any retuning decided then uses the December report, not intuition.

## Constraints and conventions

- Business logic stays in pure/report functions; CLI stays thin.
- No AI attribution in commits; Conventional Commits only.
- Golden baselines regenerated only for intended surface changes.
- Forecast authored lines ~900-1200 (tool+tests ~550, on-page ~50, linking
  ~40, posts ~350). Exceeds the ~400 advisory: delivery strategy
  `ask-on-risk` — ask the user once for the chain strategy before the first
  oversized commit.

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`: `strict_tdd: true`,
`apply.tdd: true`). Runner: `venv/bin/python -m pytest`.

**Known environmental failures (pre-existing on main @ `917b4e7`, verified
via a detached temp worktree — NOT campaign regressions):** 8 failures in
`tests/test_e2e.py` (2, playwright) and `tests/test_scraper.py` +
`tests/test_refresh_catalog.py` (6, async/ordering). Campaign acceptance for
full-suite runs: zero NEW failures vs this baseline (568 passed / 8 failed
observed on the branch).

Observed results: (to be recorded per task)

- T1: `venv/bin/python -m pip install -r requirements-search-console.txt`
  succeeded (`Successfully installed requests-2.32.3`). The venv's
  pre-existing requests 2.32.5 was downgraded to the pinned 2.32.3.
- Plan task 2: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
  RED `ModuleNotFoundError: No module named 'gsc_report'` -> GREEN
  `3 passed` (pure aggregation + seasonal matcher).
- Plan task 3: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
  RED `ImportError: cannot import name 'build_low_ctr' from 'gsc_report'` ->
  GREEN `9 passed` (4 view builders + task 2 amendment: the degenerate
  weighted-average fixture was strengthened to impressions 100/10 so the
  weighted position ≈5.18 is actually pinned, not equal to the unweighted
  mean).
- Plan task 4: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
  RED `ImportError: cannot import name 'render_markdown' from 'gsc_report'`
  (file-level collection error) -> GREEN `11 passed` (markdown emitter +
  task 3 amendment: half-open window bounds pinned — exactly 5.0 included,
  exactly 20.0 excluded; `min_impressions` filter bites (impressions 5 < 10
  out); ctr threshold bites (0.10 >= 0.03 out). Amendment status was
  observed pre-emitter as `9 passed`, confirming the new fixture rows broke
  no existing assertion).
- Plan task 5: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
  RED `ImportError: cannot import name 'fetch_rows' from 'gsc_report'`
  (file-level collection error) -> GREEN `14 passed` (service-account auth +
  paginated fetch with backoff; fake transport only, no network). Three
  plan-text defects were verified empirically with venv-interpreter probes
  and minimally amended before RED, each forced by this task's own pinned
  observables (14 passed; sleeps exactly [1, 2, 4]; "start < end" sanity):
  (a) the sanity assert chained as `startDate > endDate is False` evaluates
  as `(a > b) and (b is False)` — unsatisfiable for any string date — and
  was parenthesized to preserve the commented "start < end" intent
  (interpreter emitted a SyntaxWarning for the chained `is`); (b) a
  single-429 fixture can never produce the pinned [1, 2, 4] ladder (probe:
  the plan's loop yields sleeps == [1]) — the fixture now returns 429 three
  times then succeeds, and the retry loop is initial call + 3 retries
  (`range(4)`, sleep after attempts 0-2) so the ladder completes and a 4th
  consecutive failure falls through to raise; (c) with the plan's
  short-page stop rule the pagination test makes 2 calls, not 3 (probe: 2) —
  expected calls amended 3 -> 2, the provisioned third page kept as an
  over-fetch canary; same expected-count arithmetic slip class already
  fixed once in plan task 2 (f472f8c).
- Plan task 6: `venv/bin/python -m pytest tests/test_gsc_report.py -v`.
  Pre-main amendment pre-status observed first (task 4 technique, verbatim
  plan tests): (a) float-formatting FAILED (its genuine RED driver),
  (b) FAILED `assert 1 == 2`, (c) retry-exhaustion PASSED (pins existing
  code). Plan defect in (b), same slip class as plan tasks 2/5: with
  `min_impressions=100` V3 can never be empty because "regalos navidad"
  carries 200 impressions (>= 100) at position 3.0 with ctr 0.025 — the
  failure output renders that V3 row — so the pinned
  `md.count("No data") == 2` ("V2 and V3 empty") is unreachable; the
  literal was amended 100 -> 1000 per the plan's own rationale ("an empty
  V3 proves the threshold was passed"), after which the corrected test
  passes pre-main, confirming it pins the existing knob pass-through.
  Then full RED: appending the `main` test gave
  `ImportError: cannot import name 'main' from 'gsc_report'` (file-level
  collection error) -> GREEN `18 passed`, not the plan's "17 (14 existing
  + 3 new)": the plan itself specifies four new tests (main + three
  amendments), so 14 + 4 = 18. Amendment code touches applied exactly as
  specified (`_table` floats at 2 decimals with ints unchanged, token file
  `chmod(0o600)` after write, 504 added to the retryable set). Smoke:
  `venv/bin/python tools/gsc_report.py --help` exited 0 with the full flag
  list (argparse exits before any credential load).
- Plan task 6 readiness fixes (quality review of the GSC report CLI): (a)
  `.gitignore` gap — `docs/gsc-setup-guide.md` Option B references
  `tools/gsc_client_secret.json`, but only `tools/gsc_service_account.json`
  and `tools/reports/` were ignored; the OAuth client-secret path is now
  ignored too. Proof: `git check-ignore -v tools/gsc_client_secret.json` ->
  `.gitignore:47:tools/gsc_client_secret.json`. (b) Error-body surfacing:
  RED `test_fetch_rows_surfaces_api_error_body` FAILED — a real 403 (e.g.
  service account added but permissions not propagated) surfaced as the
  opaque `RuntimeError: HTTP 403` (regex 'sufficient permissions' did not
  match) -> GREEN `19 passed`: `fetch_rows` wraps `raise_for_status()` and
  re-raises `RuntimeError("GSC API error ({status}): {first 500 chars of
  body}")` chained from the original exception; the existing retry tests
  stay green because the fake's RuntimeError and requests' HTTPError are
  both caught and re-wrapped. One fake amendment: `_FakeResponse` gained a
  `text` property (json.dumps of the payload) — the plan-verbatim GREEN
  implementation reads `response.text`, which the fake lacked, so without
  it the pinned `19 passed` observable was unreachable.
- Plan task 7: country code fix. Verified empirically against the real API:
  the Search Console country dimension uses ISO 3166-1 alpha-3 codes (`esp`,
  `arg`, `chl`), not alpha-2 — the real property has 49 impressions from
  `esp` in 90 days, while the old `es`-filtered query returned zeros, and a
  baseline run with `--country esp` works. RED
  `test_fetch_rows_country_defaults_to_alpha3_esp` FAILED
  `AssertionError: assert 'es' == 'esp'` -> GREEN `20 passed` (19 existing
  + 1 new). `test_fetch_rows_paginates_until_short_page` stays green: it
  passes `country="es"` explicitly and pins pass-through, not the default.
  Changes: `fetch_rows` default `country="esp"` (+ docstring alpha-3 note),
  argparse `--country` default `esp` + help text, guide Notes bullet.
- Plan task 8: organizer landing visible FAQ + FAQPage schema + `/ideas`
  anchor. RED `venv/bin/python -m pytest tests/test_seo_landings.py -v -k
  "category_ideas or visible_faq"` -> `2 failed, 73 deselected`
  (`test_organizer_landing_links_category_ideas`: `assert None`, no `/ideas`
  anchor; `test_organizer_landing_has_visible_faq_and_faqpage_schema`:
  `assert faq_heading` -> `None`). Template change purely additive (36
  insertions, 0 deletions; title/description/H1 byte-identical per the T4
  "keep verbatim" decision). Full-file run then showed `2 failed, 73
  passed`: the only failures were the two pre-campaign FAQPage-exclusion
  assertions — `test_shared_metadata_is_valid_and_does_not_invent_claims[/amigo-invisible]`
  at its `assert all(item["@type"] != "FAQPage" ...)` line, and
  `test_faqpage_is_confined_to_category_landings` -> `AssertionError:
  /amigo-invisible` — stale against the T4-recorded mandate that the
  organizer landing emits FAQPage. Minimal amendment observed before GREEN:
  the exclusion in the metadata test is scoped with
  `if path != "/amigo-invisible"` (its SoftwareApplication and
  unsupported-claims checks for that path unchanged), and the confinement
  test was renamed `test_faqpage_does_not_leak_onto_unrelated_pages` with
  `/amigo-invisible` removed from its path list (the leak guard for `/`,
  `/catalog`, `/blog` and the blog post kept). GREEN full file `75 passed`
  (includes `test_every_json_ld_block_is_valid_json[/amigo-invisible]` on
  the new block and the untouched title assertion). Subset
  `venv/bin/python -m pytest tests/ -q -k "seo or christmas or editorial"`
  -> `160 passed, 426 deselected`; no golden baseline touched.
- Plan task 9: organizer aside driven by a per-post config flag. RED
  `venv/bin/python -m pytest tests/test_seo_landings.py -v -k aside` ->
  `1 failed, 63 deselected` (`test_organizer_aside_matches_config_flag`:
  `AssertionError: regalos-amigo-invisible-10-euros` — the flag-less config
  contradicted the hard-coded aside on the 10-euros page). GREEN
  `venv/bin/python -m pytest tests/test_seo_landings.py
  tests/test_editorial_filtering.py -v` -> `96 passed`, including the Task 8
  quality-review amendment appended to
  `test_organizer_landing_has_visible_faq_and_faqpage_schema` (FAQPage
  `mainEntity` cardinality pinned at 3 and rendered answer paragraphs pinned
  equal to each question's `acceptedAnswer.text`); golden baseline
  `test_off_mode_matches_golden_baseline[blog]` untouched (aside output
  byte-identical — flag-driven, same markup). Jinja dict-attribute
  assumption held: `post.organizer_aside` on a flag-less dict resolves
  falsy (no aside), so no `post.get()` fallback was needed. Extra suite
  `venv/bin/python -m pytest tests/test_christmas_guide.py -v` -> `14
  passed` (`test_christmas_guide_does_not_show_the_organizer_aside` stays
  green: no flag, no aside).

- Plan task 10: optional per-post `guide` sections (heading + paragraphs)
  rendered between the post header and the organizer aside. RED
  `venv/bin/python -m pytest tests/test_blog_guide_sections.py -v` ->
  `1 failed`: status 200 (the fixture post renders), then
  `assert 'Sección uno' in body` FAILED — feature missing, not an error.
  `post.get("guide", [])` did NOT raise for guide-less dicts (Jinja dict
  `.get` resolves fine), so the plan's `or []` fallback was unnecessary.
  First GREEN run of the three authorized suites gave `1 failed, 46
  passed`: `test_off_mode_matches_golden_baseline[blog]` drifted even
  though no current post has `guide`. Root cause: default `Jinja2Templates`
  has no `trim_blocks`, so with an empty/missing `guide` the bare
  `{% for %}` / `{% endfor %}` tag lines still render as whitespace lines,
  changing bytes on every existing blog post. Regenerating the golden was
  rejected (it would bake whitespace noise into all guide-less posts,
  contradicting the plan's own "posts without `guide` render nothing new").
  Minimal amendment honoring the pinned byte-identical observable: Jinja
  whitespace control on the outer loop tags (`{%- for ... %}` /
  `{%- endfor %}`), so an absent `guide` emits zero bytes between the
  header `</div>` and the organizer-aside `{% if %}` line; the inner
  paragraphs loop stays plan-verbatim (its whitespace only appears inside
  rendered sections). After the amendment: `venv/bin/python -m pytest
  tests/test_blog_guide_sections.py tests/test_editorial_filtering.py
  tests/test_christmas_guide.py -v` -> `47 passed`, blog golden file
  untouched.

- Plan task 11: three text-only informational amigo-invisible guides
  (`como-organizar-amigo-invisible`, `reglas-del-amigo-invisible`,
  `frases-para-el-amigo-invisible`) consuming both the task 9
  `organizer_aside` flag and the task 10 `guide` sections, with copy taken
  byte-identical from the plan. RED `venv/bin/python -m pytest
  tests/test_christmas_guide.py -v` -> `3 failed, 14 passed`: each new
  parametrized case failed with `assert 404 == 200` (posts did not exist);
  all pre-existing christmas assertions stayed green. GREEN same command ->
  `17 passed` (single H1 equals the configured title, canonical, at least
  two `<h2>` guide headings, `/amigo-invisible` aside link present, URL in
  sitemap.xml; `test_christmas_guide_does_not_show_the_organizer_aside`
  stays green). Intended golden drift: `venv/bin/python -m pytest
  tests/test_editorial_filtering.py -q` -> `1 failed, 31 passed` — only
  `test_off_mode_matches_golden_baseline[sitemap]`. Regenerated with
  `venv/bin/python -m pytest tests/test_editorial_filtering.py
  --editorial-update-baselines` -> `32 passed`; `git diff
  tests/baselines/editorial_off_sitemap.html` shows EXACTLY the three new
  `<url>` blocks (18 insertions, 0 deletions) — no other golden touched.
   Re-run `venv/bin/python -m pytest tests/test_editorial_filtering.py
   tests/test_seo_landings.py -q` -> `99 passed`. Commit `5856d32`.

- Plan task 12: multi-category blog criteria. `criteria.categories` (list of
  category names) is now resolved with `slugify` into a union search with a
  shared `limit` and cross-category ASIN de-dup in `get_blog_post_detail`;
  `get_blog_posts_with_covers` resolves covers from the first category with a
  visible product; max_price-only posts keep the historical whole-catalog
  search (`slugs = [None]`); the hero fallback moved into a module-level
  `_hero` helper. Two plan-text amendments recorded: (a) the plan's RED/GREEN
  selector `-k multi_cat` matches nothing because the plan names the test
  `test_get_blog_post_detail_accepts_category_list`; the run used
  `-k accepts_category_list` instead; (b) the plan's literal
  `return _hero(post, products)` returns a bare dict from a function whose
  contract is the 2-tuple `(post, products)` (16 `main.py` callers unpack two
  values) — first GREEN attempt failed with `ValueError: too many values to
  unpack (expected 2)`; both exits now return `_hero(post, products),
  products`, keeping the plan's helper body verbatim. RED
  `venv/bin/python -m pytest tests/test_catalog.py -v -k accepts_category_list`
  -> `1 failed`: the categories list was ignored and the whole-catalog
  fallback leaked `alimentacion-y-bebidas` into the result categories. GREEN
  same command -> `1 passed` (test seeds a minimal second-category product
  `T1` in `juguetes-y-juegos` so both requested categories are exercised).
  Regression gate `venv/bin/python -m pytest tests/test_catalog.py
  tests/test_editorial_filtering.py tests/test_christmas_guide.py
  tests/test_seo_landings.py -q` -> `1 failed, 173 passed`: the only failure,
  `test_get_blog_posts_with_covers_uses_distinct_images_for_overlapping_criteria`,
  is PRE-EXISTING — reproduced byte-identical at HEAD `c02da2f` in a
  throwaway `git worktree` (removed afterwards), so it is not a task 12
  regression; it is not in the task's known-environmental-failures list and
  is left for the parent to triage. Commit `7a987e2`.

- Task 12 bugfix: criteria-less posts. Bug evidence: at HEAD `dc75888` the
  informational posts (no `criteria` key: `como-organizar-amigo-invisible`,
  `reglas-del-amigo-invisible`, `frases-para-el-amigo-invisible`) rendered the
  WHOLE catalog below the guide — `GET /blog/como-organizar-amigo-invisible`
  rendered 3679 product cards (verified empirically by the parent on the real
  catalog); the unit seed reproduces it as `get_blog_post_detail` returning all
  3 seeded products for a criteria-less post. Root cause: the task 12 else-branch
  `slugs = [None]` whole-catalog fallback, designed for max_price-only posts,
  also fired for posts with no criteria at all, and criteria-less posts consumed
  images in the covers de-dup. RED `venv/bin/python -m pytest
  tests/test_catalog.py -v -k "criterialess or distinct_images"` -> `2 failed`:
  new `test_get_blog_post_detail_criterialess_post_has_no_products` (assert
  `products == []` got the 3-product catalog) and the pre-existing covers-dedup
  failure (`assert 'img-cheap-1.jpg' == 'img-cheap-2.jpg'`). New max_price guard
  test `test_get_blog_post_detail_max_price_only_post_keeps_catalog_search`
  (no such test existed) passes pre- and post-fix, pinning the historical
  whole-catalog behavior for `regalos-baratos-menos-20-euros`. First fix
  attempt scoped the `[None]` fallback to max_price-only posts and regressed 6
  `tests/test_christmas_guide.py` probe tests — verified NOT pre-existing by
  restoring HEAD's else-branch byte-identically (`git diff services.py` empty)
  and re-running: `7 passed` with the same `-k` selector. Those probes
  monkeypatch `services.BLOG_POSTS` with posts that HAVE a `criteria` key
  (`{}` or `{"limit": N}`) and pin the old whole-catalog semantics; after
  `post.get("criteria", {})` the code cannot distinguish them from
  no-criteria-key posts, so a max_price-only scoping and the suite's ALL-green
  criterion were mutually exclusive. Resolution (parent-approved): both
  `get_blog_post_detail` and `get_blog_posts_with_covers` now derive
  `has_criteria = "criteria" in post` BEFORE the `.get("criteria", {})` default
  and keep the whole-catalog `[None]` fallback for ANY criteria-bearing post
  without a category filter (limit-cappable; max_price-only posts flow through
  unchanged), while posts with NO criteria key resolve `slugs = []` —
  text-only informational guides render no products by design. GREEN
  `venv/bin/python -m pytest tests/test_catalog.py -v -k "criterialess or
  distinct_images or accepts_category_list"` -> `3 passed`; full
  `tests/test_catalog.py` -> `60 passed`. Render sanity (TestClient, in-memory
  seed): `GET /blog/como-organizar-amigo-invisible` -> status 200,
  `product-card count == 0`, empty state `No encontramos productos` present,
  guide heading `Cómo funciona el amigo invisible` present. Regression gate
  `venv/bin/python -m pytest tests/test_catalog.py
  tests/test_editorial_filtering.py tests/test_christmas_guide.py
  tests/test_seo_landings.py tests/test_blog_guide_sections.py -q` ->
  `177 passed, 0 failed` (the 6 christmas probes pass UNCHANGED). Commit
  `62c3744`.
- Plan task 13: `venv/bin/python -m pytest tests/test_christmas_guide.py -v`
  RED `2 failed, 17 passed` — both new
  `test_audience_post_renders_curated_products[...]` cases hit
  `assert 404 == 200` (slugs unconfigured). The client fixture's in-memory
  DB is empty, so the test seeds one visible product per post's leading
  category (Electrónica at 12.99 €, under the coworkers 15 € cap; Juguetes
  y juegos for the kids post) and additionally asserts a non-empty
  `product-card` grid — both are curated lists. GREEN after adding the two
  `blog_config.py` entries (first production consumers of the task 12
  `criteria.categories` + `limit`): `19 passed`. Sitemap golden:
  `venv/bin/python -m pytest tests/test_editorial_filtering.py -q` ->
  `1 failed, 31 passed` (`test_off_mode_matches_golden_baseline[sitemap]`,
  drift = the 2 new URLs, intended); regenerated ONLY the sitemap with
  `--editorial-update-baselines` -> `32 passed`; `git diff
  tests/baselines/editorial_off_sitemap.html` shows EXACTLY the two new
  `<url>` blocks (12 inserted lines, 0 deletions). Regression gate
  `venv/bin/python -m pytest tests/test_catalog.py
  tests/test_editorial_filtering.py tests/test_christmas_guide.py
  tests/test_seo_landings.py tests/test_blog_guide_sections.py -q` ->
  `181 passed` (179 pre-existing green + the 2 new audience tests; the
  plan's "179 = 177 + 2" arithmetic was stale by 2 on the pre-existing
  baseline — the observed delta vs the pre-task suites is exactly the 2 new
  tests, proven by RED collecting 17 -> 19 in test_christmas_guide.py).
  Copy is the user-approved T4 defaults, byte-identical to the plan text.
   Human product review of the rendered lists PENDING (post-commit;
   requested swaps would be a follow-up `fix(blog):` criteria tweak — the
   criteria are plain config). Commit `02dcfaa`.
- Plan task 13 curation swap: the user reviewed a curated candidate board
  and APPROVED 15+15 ASINs, so both audience posts switched from the task 12
  mechanical `criteria.categories`+`limit` to hand-curated
  `criteria["items"]` (same WU-2 mechanism as the christmas guide; the
  categories/limit mechanism stays in `services.py` as a live mechanism).
  Mechanical lists had rendered badly (19/20 batteries for coworkers;
  costumes + a 136,99 € box for kids). Covers fix (RED first):
  `get_blog_posts_with_covers` ignored `criteria["items"]` and did a
  whole-catalog search for items-posts — the christmas card's cover was a
  random product's image (latent defect). New items branch resolves the
  cover via `products_by_asins` with the same dedup/fallback semantics as
  the category branch; RED
  `test_get_blog_posts_with_covers_uses_curated_items` failed with
  `img-bystander.jpg` (unrelated product's image picked) -> GREEN. Audience
  render test seeds the real first-two ASINs per post and asserts the first
  curated ASIN renders, pinning the items path. Regression gate
  `venv/bin/python -m pytest tests/test_catalog.py
  tests/test_editorial_filtering.py tests/test_christmas_guide.py
  tests/test_seo_landings.py tests/test_blog_guide_sections.py -q` ->
  `182 passed` (181 pre-existing + the 1 new covers test); sitemap golden
  UNCHANGED as expected (URLs identical). Real-catalog render sanity
  (read-only): both posts return exactly 15 products in the approved order
  (first: "El Hombre en busca de Sentido" 12,25 € / "Virus ..." 12,99 €),
  all 30 ASINs resolve with 0 missing and 0 dupes; all three items-posts
  (christmas included) now show covers from their own curated products.
  Commit `417ac55`.
- Plan task 14: appended the characterization test
  `test_home_links_the_christmas_guide` to `tests/test_seo_landings.py`
  (reusing the file's `page()` helper). Plan-text amendment: the plan's
  `-k christmas_guide_link` expression matched nothing (the test name in the
  plan's own snippet, `test_home_links_the_christmas_guide`, has no `_link`
  suffix); ran with `-k christmas_guide`. RED
  `1 failed, 69 deselected` — no anchor to
  `/blog/regalos-navidad-mas-deseados` in home main. Added the anchor in
  `templates/index.html`'s "Listas para Navidad y amigo invisible" section
  next to the existing `/amigo-invisible` link, matching its
  markup/classes. GREEN `1 passed`. Home golden drift was EXACTLY the new
  anchor; regenerated ONLY `editorial_off_home.html` with
  `--editorial-update-baselines`; `git diff tests/baselines/` shows exactly
  1 inserted line, 0 deletions. Validation
  `venv/bin/python -m pytest tests/test_seo_landings.py
  tests/test_editorial_filtering.py -q` -> `102 passed`. Commit `5fe70bc`.

## Review workload and delivery

| Work unit | Commits | Authored +/- (git numstat) |
| --- | --- | ---: |
| T1 setup guide + deps + ignores | `adb8032` | ~43 |
| T2 pure layer | `dc4c22c` | ~82 |
| T3 report views | `6d2df2c` | ~112 |
| T4 emitter | `0201e4a` | ~61 |
| T5 auth + fetch | `fc36f5f` | ~174 |
| T6 CLI + readiness fixes | `513c04f`, `a07ef9d`, `fa9a8d4` | ~133 |
| T7 country-code fix | `a0b0b43`, `a1ec4ef` | ~18 |
| T8 on-page FAQ + schema | `1476794` | ~69 |
| T9 aside flag | `e76f06a` | ~22 |
| T10 guide sections | `96b4c82` | ~30 |
| T11 informational posts | `5856d32`, `c02da2f` | ~111 |
| T12 multi-category + criteria-less fix | `7a987e2`, `62c3744` | ~178 |
| T13 audience posts + curated swap | `02dcfaa`, `417ac55` | ~232 |
| T14 home -> christmas link | `5fe70bc` | ~7 |
| **Total (code, docs commits excluded)** | 44 commits on branch | **1,231** |

- **Delivery: `single-pr`** (user decision, 2026-11-03): the branch
  `feature/amigo-invisible-seo-campaign` goes to one PR against `main`;
  push/PR/merge are user-owned.
- RDD assess at close: **medium, `review_due: false` (`under_budget`)** —
  no native review triggered for the slice.
- Final full-suite gate: **583 passed / 8 failed** — the 8 are the
  pre-existing environmental failures verified on `main` (see above); zero
  new failures.
- RDD is on (global). Known machine issue: native reviewer sub-agent
  sometimes returns empty output (`opencode_task_output_empty`); surface to
  the user if it recurs.

## Rollback

Additive feature: new CLI tool + tests, config/blog entries, template
tweaks, linking. Revert the work-unit commits in reverse order. No
credential, migration, or production-data changes. `.gitignore` additions
are harmless.

## Progress

- [x] Exploration: SEO surface inventory, roadmap alignment (#932 item 4),
      blog/aside/criteria mechanisms mapped.
- [x] Product decisions: approach A; full scope; credentials guided; SA-first.
- [x] Design presented and approved (2026-11-02).
- [x] T1 — credential setup + config plumbing (setup guide, local deps,
      secret ignores).
- [x] Plan task 2 — pure GSC row aggregation and seasonal matcher
      (`tools/gsc_report.py`, `tests/test_gsc_report.py`).
- [x] Plan task 3 — GSC report view builders (V1 top queries, V2
      opportunities, V3 low CTR, V4 per-url) + task 2 weighted-average test
      amendment (`tools/gsc_report.py`, `tests/test_gsc_report.py`).
- [x] Plan task 4 — markdown emitter for the GSC report (`render_markdown`
      + `_table`) + task 3 surviving-mutant coverage amendment
      (`tools/gsc_report.py`, `tests/test_gsc_report.py`).
- [x] Plan task 5 — GSC service-account auth and paginated fetch with
      backoff (`load_credentials`, OAuth fallback, `fetch_rows` against a
      fake transport; three plan-text amendments recorded under Observed
      results) (`tools/gsc_report.py`, `tests/test_gsc_report.py`).
- [x] Plan task 6 — GSC report CLI entrypoint with flags (`main` argparse
      entry + `__main__` guard; task 4/5 review amendments: compact float
      rendering, 0600 token permissions, 504 retryable; one plan-text
      amendment recorded under Observed results) (`tools/gsc_report.py`,
      `tests/test_gsc_report.py`).
- [x] Plan task 6 readiness fixes — `.gitignore` OAuth client-secret path
      + error-body surfacing in `fetch_rows` on non-retryable GSC failures
      (quality-review findings; `_FakeResponse` text amendment recorded
      under Observed results) (`.gitignore`, `tools/gsc_report.py`,
      `tests/test_gsc_report.py`).
- [x] Plan task 7 — GSC country code fix: default filter uses ISO 3166-1
      alpha-3 (`esp`), verified against the real API (evidence under
      Observed results) (`tools/gsc_report.py`, `tests/test_gsc_report.py`,
      `docs/gsc-setup-guide.md`).
- [x] T4 checkpoint — baseline run (sc-domain, esp) + defaults confirmed
      by the user; targets recorded in "T4 targets" above.
- [x] Plan task 8 — organizer landing visible FAQ (3 Q&As) + matching
      FAQPage JSON-LD + `/ideas` anchor in the ideas section; two stale
      FAQPage-exclusion assertions aligned with the T4 mandate (evidence
      under Observed results) (`templates/amigo_invisible.html`,
      `tests/test_seo_landings.py`).
- [x] Plan task 9 — organizer aside driven by a per-post `organizer_aside`
      config flag (hard-coded slug check removed; FAQ test strengthened with
      answer byte-identity + schema cardinality per the Task 8 quality
      review; evidence under Observed results) (`blog_config.py`,
      `templates/blog_post.html`, `tests/test_seo_landings.py`).
- [x] Plan task 10 — optional per-post `guide` sections (text-only
      heading + paragraphs) rendered between the post header and the
      organizer aside; one plan-text amendment recorded under Observed
      results (Jinja whitespace control so guide-less posts stay
      byte-identical) (`templates/blog_post.html`,
      `tests/test_blog_guide_sections.py`).
- [x] Plan task 11 — three text-only informational amigo-invisible guides
      (organize, rules, phrases) using the task 9 `organizer_aside` flag
      and the task 10 `guide` sections; sitemap golden regenerated with
      exactly the three new `<url>` blocks (evidence under Observed
      results) (`blog_config.py`, `tests/test_christmas_guide.py`,
      `tests/baselines/editorial_off_sitemap.html`).
- [x] Plan task 12 — multi-category blog criteria: `criteria.categories`
      union search with shared `limit` and ASIN de-dup in
      `get_blog_post_detail`, same slug resolution for covers; max_price-only
      posts keep the whole-catalog fallback; two plan-text amendments and one
      pre-existing (non-task) covers-dedup test failure recorded under
      Observed results (`services.py`, `tests/test_catalog.py`).
- [x] Task 12 bugfix — criteria-less informational posts render no products
      (criteria-key-presence fallback: whole-catalog search kept for
      criteria-bearing posts, no products for no-criteria-key posts;
      RED/GREEN, render sanity and `177 passed` regression gate with the
      christmas probes unchanged recorded under Observed results)
      (`services.py`, `tests/test_catalog.py`).
- [x] Plan task 13 — two curated audience blog posts (coworkers, kids)
      using the task 12 `criteria.categories` + `limit`; parametrized
      render/sitemap tests with a non-empty `product-card` assertion;
      sitemap golden regenerated with exactly the two new `<url>` blocks;
      human product review PENDING (evidence under Observed results)
      (`blog_config.py`, `tests/test_christmas_guide.py`,
      `tests/baselines/editorial_off_sitemap.html`).
- [x] Plan task 13 curation swap — user-approved 15+15 ASIN hand-curated
      `criteria["items"]` for both audience posts (mechanical lists rendered
      badly); covers items branch fix for items-posts (latent christmas
      random-cover defect); render sanity 15/15 approved order, 30/30 ASINs
      resolve; sitemap golden unchanged (evidence under Observed results)
      (`blog_config.py`, `services.py`, `tests/test_christmas_guide.py`,
      `tests/test_catalog.py`).
- [x] Plan task 14 — home links the christmas guide (characterization
      test first: RED, link absent -> added the anchor next to the
      `/amigo-invisible` link -> GREEN; home golden regenerated with
      exactly the 1 new anchor line; one plan-text amendment recorded
      under Observed results) (`templates/index.html`,
      `tests/test_seo_landings.py`,
      `tests/baselines/editorial_off_home.html`).
- [x] T2..T8 implementation.
- [ ] T9 December re-measure — REMINDER: first week of December 2026, run
      `venv/bin/python tools/gsc_report.py --days 90 --site
      sc-domain:regalame.app --out tools/reports/gsc-december.md` and
      compare against `tools/reports/gsc-baseline-2026-11-03.md` (the
      esp-filtered run); record the outcome here.
- [x] Close-out: full suite 583 passed / 0 new failures; delivery strategy
      `single-pr` chosen by the user (2026-11-03).
