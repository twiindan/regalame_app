# Mobile performance: Phase A fixes (roadmap item 6)

Roadmap item 6 of the persisted roadmap `seo/next-improvements-roadmap` (Engram #932):
"mobile performance measurements then demonstrated bottleneck fixes". This is the only ODD
planning artifact for this feature.

## Objective and problem

The app ships several third-party assets on every page. A measured mobile baseline shows
the bottleneck is download weight and render-blocking third parties (TBT and CLS are
already 0), dominated by an icon web-font bundle that loads unused weights and by
render-blocking Google Fonts.

## Measured baseline (local, Lighthouse 13.5.0, default mobile: Slow 4G + 4x CPU)

Server: uvicorn on a copy of `database.db` (`DOMAIN_URL=http://localhost:8099`).

| Page | Score | FCP | LCP | TBT | CLS | Weight | Third-party |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `/` | 75 | 4133 ms | 4307 ms | 0 | 0 | 419 KB | 403 KB |
| `/catalog` | 63 | 5918 ms | 6087 ms | 0 | 0 | 970 KB | 842 KB |

Heaviest catalog requests: `Phosphor-Bold.woff2` 147 KB, `Phosphor-Fill.woff2` 129 KB,
catalog HTML 128 KB, Tailwind Play CDN 124 KB, Inter fonts 157 KB (110 + 47 KB), Amazon
images 181 KB. Phosphor CSS: 7 weights, ~84 KB.

`templates/` uses only `ph-bold`, `ph-fill`, `ph-duotone` and regular `ph`; `ph-light` and
`ph-thin` CSS load but are never used. Inter weights used: `font-normal` (400),
`font-medium` (500), `font-semibold` (600), `font-bold` (700), `font-extrabold` (800);
`font-light` (300) is unused.

Candidate is measured locally: no CDN edge caching and a localhost server (1-48 ms); this
is a reproducible baseline, not a production field measurement.

## Authorized scope and boundary (Phase A)

User chose Phase A: fix fonts and Phosphor without touching the no-Node/no-bundler
convention.

- Self-host the Inter **latin variable** woff2 (weight 400-800) as a static asset; drop the
  Google Fonts stylesheet and its third-party origins; keep `font-display: swap`.
- Load only the Phosphor weights actually used (regular, bold, fill, duotone); drop the
  full-weight bundle (`light`, `thin` and the loader script).
- Out of scope: Tailwind Play CDN (needs the no-Node decision), Phosphor-to-inline-SVG
  refactor, HTMX self-hosting, catalog document size, Amazon image optimization.

## Measured result (Phase A, same environment)

| Page | Score | FCP | LCP | Weight | Requests |
| --- | ---: | ---: | ---: | ---: | ---: |
| `/` | 75 -> **90** | 4133 -> 2913 ms | 4307 -> 2913 ms | 419 -> 393 KB | 16 -> 12 |
| `/catalog` | 63 -> **68** | 5918 -> 4810 ms | 6087 -> 5417 ms | 970 -> 836 KB | 25 -> 20 |

Inter third-party fonts (157 KB across `fonts.googleapis.com`/`fonts.gstatic.com`) are
replaced by one self-hosted 47.5 KB latin variable woff2; the unused Phosphor `light`/`thin`
stylesheets and the bundle loader no longer load.

## Tasks and acceptance

- [x] **T1 — Self-host Inter.** Add `static/fonts/inter-latin.woff2` +
  `static/css/fonts.css` (`@font-face`, `font-weight: 400 800`, `font-display: swap`);
  base.html preloads the font and links the local CSS; no `fonts.googleapis.com` /
  `fonts.gstatic.com` reference remains.
- [x] **T2 — Phosphor used weights only.** base.html links the four weight stylesheets
  instead of the bundle script; no `light` / `thin` / bundle loader.
- [x] **T3 — Regression tests.** New `tests/test_assets.py` asserting no Google Fonts /
  bundle references, the four Phosphor weights present, and the font asset existing.
- [x] **T4 — Golden baselines.** Regenerate the nine `editorial_off_*.html` snapshots;
  review that the only diff is the head asset lines.

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`). Runner:
`/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest`.

Checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_assets.py
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines
```

Post-fix measurement: re-run the same Lighthouse mobile runs on `/` and `/catalog` and
report the before/after delta.

## Delivery and rollback

- Delivery: `single-pr` on `feature/mobile-perf` (base `main` @ `a9ac899`); PR/merge
  user-owned.
- Rollback: revert the commits; restores the Google Fonts link and the Phosphor bundle.
  No data, migration, or behavior change — only asset delivery.

## Progress

- [x] Baseline measured (home 75 / catalog 63).
- [x] Scope decided: Phase A.
- [x] T1-T4.
- [ ] Push / PR / merge — user-owned, pending explicit go-ahead.
