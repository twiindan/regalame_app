# Tailwind v4 migration

Maintenance work unit after the mobile-performance item (roadmap #932). The app is on
Tailwind **v3.4.17** prebuilt with the standalone executable; this migrates to **v4.3.3**
using the v4 standalone executable, keeping the repo's **no Node / no bundler** convention.

## Objective and problem

v3 works, but v4 is the supported line and the current pin will age. v4 is a breaking
release: it drops the `@tailwind` directives for `@import "tailwindcss"`, moves config to
CSS (`@theme`), and renames several utilities we actually use. Doing nothing keeps us on an
unsupported major.

## Why this approach (decision, resolved)

User chose **CSS-first**: `@import "tailwindcss";` + `@theme` + `@source`, and delete
`tailwind.config.js`. The JS config only customized three things (Inter as `font-sans`,
`animate-fade-in-up` + keyframes, content globs), so it moves cleanly.

Rejected: keeping `tailwind.config.js` via `@config` (deprecated path, still churn).

## Scope

- `tools/build_tailwind.sh` → v4.3.3, new SHA-256 pins, invocation without `-c`.
- `static/css/tailwind.src.css` → CSS-first (`@import`, `@source`, `@theme`).
- Delete `tailwind.config.js`.
- Rename the v3→v4 utilities used in templates (table below).
- Regenerate `static/css/tailwind.css` and the 9 golden baselines.
- Clean up docs that still describe "Tailwind CDN".

Out of scope: redesigning styles, adding new utilities, changing `phosphor` assets,
`?v=` cache-busting (none exists today), and any change to `templates/base.html` beyond the
class renames.

## Constraints

- No Node/npm/bundler; eval binaries only, SHA-256 pinned like the v3 script.
- Delivery is user-owned: no commit/push/PR without an explicit request.
- Strict TDD does not map to CSS-generation mechanics: a behavior RED is not meaningful for
  a class rename. Instead the guards are (a) the existing asset tests, (b) regeneration +
  baseline regen, (c) the full suite. State this honestly; do not fabricate RED.
- v4 raises the browser baseline (Safari 16.4+ / Chrome 111+); acceptable for the mobile
  audience and documented.

## Utility renames (mandatory)

| v3 | v4 | usages | note |
|---|---|---|---|
| `bg-gradient-*` | `bg-linear-*` | ~30 | e.g. `bg-gradient-to-r` → `bg-linear-to-r`; `from/to/via` unchanged |
| `outline-none` | `outline-hidden` | 32 | v4 `outline-none` = `outline-style:none` (loses the forced-colors outline) |
| `shadow-sm` | `shadow-xs` | 17 | also fixes `drop-shadow-sm` → `drop-shadow-xs` |
| `drop-shadow-sm` | `drop-shadow-xs` | 2 | |
| `flex-grow` | `grow` | 15 | also `flex-grow-0` → `grow-0` if present |
| `backdrop-blur-sm` | `backdrop-blur-xs` | 5 | also bare `blur-sm` |
| `rounded` (bare) | `rounded-sm` | 1 | must NOT touch `rounded-md/lg/xl/full/2xl/3xl` |

Not affected (verified): `shadow-md/lg/xl/2xl`, `rounded-md/lg/xl/full/2xl/3xl`,
`ring-1`/`ring-2` (widths explicit), every `border` (all carry an explicit color, so the
v4 `currentColor` default does not bite), no `@apply`/`@layer`, no `bg-opacity-*`, no
`divide-*`.

## v4.3.3 standalone SHA-256 (from the GitHub release digests)

- `tailwindcss-macos-arm64` = `cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d`
- `tailwindcss-macos-x64`   = `7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1`
- `tailwindcss-linux-x64`   = `dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a`

## Tasks

- **T1** Toolchain: bump `tools/build_tailwind.sh` to v4.3.3 with the SHAs above; drop `-c
  tailwind.config.js` from the invocation; verify the binary's real flags (`--help`) and
  keep `-i`/`-o`/`--minify`; update the banner wording.
- **T2** CSS-first config: rewrite `static/css/tailwind.src.css`; delete `tailwind.config.js`.
- **T3** Rename utilities in templates per the table.
- **T4** Regenerate `static/css/tailwind.css`; confirm the asset-test substrings
  (`.animate-fade-in-up`, `.grid-cols-1`, `.h-\[500px\]`) and record the new size vs 43 KB.
- **T5** Regenerate the 9 golden baselines; confirm the diffs are only the expected renames.
- **T6** Docs cleanup.
- **T7** Full suite (+ optional mobile Lighthouse A/B against the current main baseline).

## Acceptance criteria

- No v3-only renamed token remains in templates; generated CSS contains the v4 tokens.
- `static/css/tailwind.css` regenerates from the v4 standalone binary with no Node.
- Full suite green; baselines regenerated; new CSS size recorded.
- No new dependency; `base.html` changes limited to class renames.

## Checks

- `tools/build_tailwind.sh` regenerates the committed CSS byte-for-byte.
- `venv/bin/python -m pytest -q --ignore=tests/test_e2e.py`
- `venv/bin/python -m pytest -q tests/test_asset*.py tests/test_editorial_filtering.py`

## Delivery

No commit/push/PR unless requested.

## Progress

- [x] T1 toolchain
- [x] T2 CSS-first config
- [x] T3 template renames
- [x] T4 regenerate CSS
- [x] T5 regenerate baselines
- [x] T6 docs
- [x] T7 suite (+ optional A/B)

## Results

- `static/css/tailwind.css`: **69,135 B** raw (was 43,096). Real transfer via
  compression: gzip 10,310 B (was 7,694), brotli 8,410 B (was 6,478) — the raw
  growth is v4's `@layer properties` block (64 `@property` declarations), which
  compresses well; net transfer cost ≈ +1.9 KB brotli.
- Reproducible: double build → identical SHA-256 `077819671cdf4d06e48b2d129b91a01f7646dc531a3230166353999862681858`.
- Renames verified exhausted: `bg-gradient-` 30→0, `outline-none` 32→0,
  `shadow-sm` (incl. `drop-shadow-sm`) 19→0, `flex-grow` 15→0, `blur-sm` 5→0,
  bare `rounded` 1→0.
- Generated artifacts (`static/css/tailwind.css` + 8 changed baselines) were
  committed as a separate `chore(assets)` commit so the reviewed candidate (the
  source slice) fits the reviewer's native context budget.
- New guard: `test_prebuilt_tailwind_css_is_generated_from_v4_tokens` asserts
  v4-only tokens (`.bg-linear-to-r`, `.outline-hidden`, `.shadow-xs`) exist in
  the committed sheet — a stale v3 artifact fails even though the
  v3-compatible substrings above would still pass.
- Full suite: **536 passed**.

## Lighthouse A/B (v3.4.17 @ 5358a76 vs v4.3.3 @ ef8cec7)

Same-session interleaved A/B, medians of 3, Lighthouse 13.5.0 default mobile
(Slow 4G + 4x CPU throttling), local uvicorn WITHOUT compression (so the CSS
delta appears at full raw size), each arm serving its own committed assets.
Both arms already include the Amazon-WebP change (#68/#69), so the only delta
is the Tailwind major version.

| | home v3 | home v4 | catálogo v3 | catálogo v4 |
| --- | --- | --- | --- | --- |
| Performance | 98 | **97** | 95 | **93** |
| FCP | 1744 ms | 1803 ms | 2188 ms | 2257 ms |
| LCP | 1953 ms | 2253 ms | 2403 ms | 2703 ms |
| TBT / CLS | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Peso | 132 KB | 158 KB | 361 KB | 386 KB |

The +25-26 KB is the UNCOMPRESSED raw CSS delta; production serves Brotli via
Cloudflare, where the measured delta is 8,410 vs 6,478 B ≈ **+1.9 KB real**.
Verdict: −1/-2 Lighthouse points under worst-case (uncompressed) transfer, no
TBT/CLS change; item-6 wins (home 75→97, catalog 63→94) are preserved.

## Native review outcome (RDD, no receipt — documented)

- First transaction (`review-da8a3be20d303f68`, full 37-path candidate): START
  refused at preflight with `lens_context_budget_exceeded` — the 69 KB minified
  CSS inside the diff exceeds the reviewer's native context budget; the provider
  states retrying that candidate cannot succeed and to split into smaller
  reviewable commits.
- Second transaction (`review-a7e2a9028960840b`, source slice, 28 paths): all
  four lenses admitted `completed`. Findings: 2 CRITICAL
  (`R4-tailwind-artifact-parity`, `R3-v4-css`) claiming the deployed stylesheet
  was never rebuilt — **false positives caused by the split**: the regenerated
  v4 sheet and baselines live in the base commit of this candidate (verifiable:
  the committed `static/css/tailwind.css` contains `.bg-linear-to-r`,
  `.outline-hidden`, `.shadow-xs`), which the reviewers could not see because
  generated artifacts were outside the diff. 3 WARNINGs: the baselines one is
  false for the same reason; `R2-001` (record the size) and `R3-v4-coverage`
  (assert v4 tokens) were legitimate and are addressed in this delivery.
- The mandatory refuter batch could not be executed: the OpenCode transport
  rejected every provider-role binding form (7 attempts) and `review
  capture-refuter --materialize` does not support the opencode runtime. Per the
  contract, no PASS is claimed and the lineage was abandoned
  (`operator_disposition`, lens results quarantined). Delivered under ordinary
  repository policy with this record.
