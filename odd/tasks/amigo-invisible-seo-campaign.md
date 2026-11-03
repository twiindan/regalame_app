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

## Review workload and delivery

| Work unit | Authored additions + deletions |
| --- | ---: |
| (to be recorded per task) | |

- **Delivery: `ask-on-risk`** (forecast exceeds the ~400-line advisory).
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
- [ ] T2..T8 implementation.
- [ ] T9 December re-measure.
