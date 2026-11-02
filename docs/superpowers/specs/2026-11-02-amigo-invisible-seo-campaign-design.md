# Amigo Invisible SEO Campaign — Design

Date: 2026-11-02
Feature doc: `odd/tasks/amigo-invisible-seo-campaign.md`
Roadmap alignment: item 4 of `seo/next-improvements-roadmap` (Engram #932),
"measured Search Console full property + page-query baseline", extended with
the Christmas campaign content the user requested.

## Context and problem

Regálame already has a mature SEO surface: SSR templates, dynamic
`sitemap.xml`/`robots.txt`, validated JSON-LD (FAQPage etc.), canonicals,
pSEO landings at `/ideas/{slug}`, an organizer landing at
`/amigo-invisible`, and a curated blog. What it lacks:

1. **No GSC tooling.** `requirements-search-console.txt` pins OAuth deps
   ("Local CLI only") but no code uses them. Search data exists (property
   configured with months of data) but is not accessible programmatically.
2. **No campaign-driven content.** Seasonal demand for "amigo invisible"
   peaks mid-November to December. Head terms ("regalos amigo invisible")
   are held by large media listicles and are not winnable. Winnable
   surfaces: tool-intent queries (lower competition, higher conversion),
   long-tail audience/price queries, and informational queries.
3. **Time pressure.** Content published after early November is unlikely to
   rank within this campaign (2-6 weeks to index/rank).

## Goal and success criteria

- A repeatable GSC report CLI in the repo that produces a decision-ready
  baseline (and can be re-run in December to measure).
- On-page and linking changes justified by that data (checkpoint with the
  user before edits).
- 3-5 new blog entries: 2-3 informational (text-only) and 1-2 curated
  audience lists ("compañeros de trabajo", "niños").
- December re-run shows measurable position/click movement on target
  queries (documented in the feature doc).

## Out of scope

- Push/PR/merge (user-owned).
- Production dependency changes; the tool is local CLI only.
- JSON-LD/canonical/sitemap policy rework beyond a FAQ-coverage check.
- Profile indexability, mobile performance (roadmap items deferred there).
- Committing any credential or token file.

## Design decisions

### D1 — Service account first, OAuth as fallback

The roadmap (#932) already noted that OAuth refresh tokens for apps in
testing mode expire after 7 days — bad for a recurring CLI. A Google Cloud
service account can be added as a property user/owner in Search Console,
needs no interactive consent, and never expires. Primary path:

1. GCP project -> enable Search Console API -> create service account ->
   download JSON key -> `tools/gsc_service_account.json` (gitignored).
2. Add the service account email as **owner** (or full user) of the
   property in Search Console settings.

Fallback: OAuth installed-app flow (deps already pinned) with the token
cached at `~/.config/regalame/gsc_token.json`. Setup guide covers both.

### D2 — One tool, four report views

`tools/gsc_report.py` fetches `searchanalytics.query` rows
(dimensions `[query, page]`, country `es`, default window 90 days,
paginated) once, then pure functions build the views:

| View | Definition | Use |
| --- | --- | --- |
| V1 top queries | Case-insensitive substring match on the stems `amigo invisible`, `regalo`, `navidad`, sorted by impressions | Market map |
| V2 opportunities | `5.0 <= position < 20.0` and `impressions >= --min-impressions` (default 10) | Pages to strengthen |
| V3 low CTR | `position <= 6.0` and `ctr < --ctr-threshold` (default 0.03) | Title/meta rework |
| V4 per-URL | Aggregate clicks/impressions/position per page | Landing health |

GSC positions are 1-based floats (averages); the bounds above apply to the
reported average. Other flags: `--days` (default 90), `--country`
(default `es`). Rows are fetched
unfiltered and filtered in the pure layer so all views share one request
budget. Empty data renders an explicit "no data" message instead of an
empty table.

### D3 — Output: stdout + optional file

Default output is stdout; `--out <path>` writes markdown (e.g.
`tools/reports/gsc-2026-11-05.md`; `tools/reports/` gitignored). No report
content is committed by default; the T4 checkpoint records targets, not
raw dumps.

### D4 — Content follows existing mechanisms

- **Informational posts** reuse the blog pipeline without products
  (empty-product rendering already exists from the curation work).
- **Audience posts** reuse `blog_config` criteria (multi-category + limit).
  The christmas-guide lesson stands: a single-category filter biases the
  list, so audience posts take a category list plus `limit`, and the
  rendered selection is human-reviewed before publish.

### D5 — Timing over perfection

The checkpoint after the baseline is one session: review findings, pick
targets, then implement. Content quality bar stays (no invented numbers,
no superlative claims — the house style of `seo_content.py`), but no
iteration loops on copy beyond one review round.

## Tool architecture

```
tools/gsc_report.py
├── auth: load_credentials()  # service account JSON, OAuth fallback
├── fetch: fetch_rows(site, days, country)  # paginated API client
├── report: build_*_views(rows, thresholds)  # pure, fixture-testable
├── emit: render_markdown(views)
└── main(): argparse CLI
```

Error handling: auth failure -> actionable setup message pointing at the
guide; quota/5xx -> exponential backoff (3 attempts) then clear failure;
empty property -> per-view "no data" notice. The tool never imports app
modules and never touches production requirements.

## Web changes

- `/amigo-invisible`: retune `<title>`, meta description, H1 and FAQ
  coverage toward observed tool-intent queries. Template tests assert the
  new copy; existing `test_seo_landings.py` expectations stay green.
- Internal linking: blog -> `/amigo-invisible`, `/amigo-invisible` ->
  `/ideas/{slug}`, home -> christmas post. The
  `regalos-navidad-mas-deseados` aside exclusion is preserved.
- New blog entries per D4; sitemap inclusion is automatic via existing
  generators.

## Testing

- Strict TDD (`openspec/config.yaml`), runner `venv/bin/python -m pytest`.
- Report builders: fixtures of API-shaped rows (empty, single, ties,
  seasonal/non-seasonal mix); auth and fetch against a fake transport — no
  network in tests.
- Template/route tests extend `test_seo_landings.py` and
  `test_christmas_guide.py` patterns (title/canonical/H1/sitemap asserts).
- Golden sitemap baseline regenerated only for intended URL additions.

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| OAuth 7-day expiry (testing mode) | D1: service account primary |
| GSC data volume too low | Configurable thresholds; explicit no-data messages; report still delivers V4 |
| Thin content on informational posts | Substantive guides, house no-invention style; only data-backed titles |
| ASIN/category lists biased (christmas-guide lesson) | Multi-category + limit; human review before publish |
| Campaign timing slips | T4 checkpoint is one session; T5-T8 sized to days, not weeks |

## Measurement

Baseline now (T4), re-run first week of December (T9). Compare positions,
clicks and CTR for the target queries recorded in the feature doc. The CLI
then remains as permanent infrastructure (roadmap item 4 delivered).
