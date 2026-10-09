# Mobile performance Phase B: prebuilt Tailwind CSS (no Node)

Continuation of roadmap item 6 (`seo/next-improvements-roadmap`, Engram #932) after
`odd/tasks/mobile-performance.md` (Phase A, merged in PR #63). This is the only ODD
planning artifact for this Phase B work unit.

## Objective and problem

`templates/base.html` loads Tailwind from the Play CDN (`https://cdn.tailwindcss.com`,
~124 KB transfer + runtime JIT compilation). It is the heaviest remaining single
third-party asset and a single point of failure: if the CDN is blocked or fails, the whole
site renders unstyled. Tailwind's own docs say the Play CDN is not for production.

Replace it with a **prebuilt static CSS** generated once by the **Tailwind v3 standalone
executable**, which runs without Node.js or npm.

## Why this approach (decision, resolved)

- Official Tailwind v3 docs: *"The CLI is also available as a standalone executable if you
  want to use it without installing Node.js."* → the repo's **no-Node / no-bundler**
  convention (`openspec/config.yaml` apply guideline) is preserved literally: no `node`,
  no `npm`, no `package.json`, no bundler enters the project, runtime, or CI.
- Chosen **v3** (not v4) for exact semantic parity with the Play CDN currently in use
  (v4 renames utilities: `shadow-sm`→`shadow-xs`, `flex-shrink`→`shrink`, …). v4 migration
  is a separate later item.
- Committing the generated artifact is the standard "no build at runtime" pattern: the
  reviewable source of truth is `tailwind.config.js` + the templates; the CSS is generated.

## Authorized scope and boundary

In scope:

- `tailwind.config.js` (v3) with content globs covering `templates/**/*.html` **and
  `main.py`** (lines ~849/1005 contain inline Tailwind classes).
- `static/css/tailwind.src.css` (the `@tailwind` input).
- `tools/build_tailwind.sh` (pinned standalone binary download + run).
- Generated, committed `static/css/tailwind.css` (minified).
- `templates/base.html`: drop the Play CDN `<script>` + inline `tailwind.config`; link the
  local stylesheet **before** the existing inline `<style>` so custom CSS still wins.
- `tests/test_assets.py`: regression assertions.
- Regenerate the eight `tests/baselines/editorial_off_*.html` snapshots.

Out of scope: Tailwind v4 migration, Phosphor→inline-SVG, catalog document size, Amazon
image optimization, HTMX self-hosting, GZip middleware.

## Tasks and acceptance

- [ ] **T1 — Regression test (RED first).** In `tests/test_assets.py`, assert the rendered
  home no longer contains `cdn.tailwindcss.com` nor a `tailwind.config` inline bootstrap,
  that it links `/static/css/tailwind.css`, and that the generated file exists and contains
  representative utilities actually used (`.animate-fade-in-up`, `.grid-cols-1`, and an
  arbitrary-value utility such as `.h-\[500px\]`).
- [ ] **T2 — Config + input CSS.** `tailwind.config.js` (content globs above; theme extend
  keeps `fontFamily.sans` → Inter and the `fade-in-up` animation/keyframes; drops the
  unused `glass`/`glassBorder` colors). `static/css/tailwind.src.css` with the three
  `@tailwind` directives.
- [ ] **T3 — Build script + generated CSS.** `tools/build_tailwind.sh` pins
  `v3.4.17` / `tailwindcss-macos-arm64`, downloads to a gitignored `tools/.bin/`, runs
  `--minify -i static/css/tailwind.src.css -o static/css/tailwind.css`, and prepends a
  "generated — do not edit" banner. `.gitignore` gains the binary cache path.
- [ ] **T4 — base.html swap.** Remove the Play CDN script and inline config; add the local
  stylesheet link in the same position (before the inline `<style>`).
- [ ] **T5 — Baselines.** Regenerate the eight `editorial_off_*.html`; confirm the only diff
  is the head asset lines.
- [ ] **T6 — Full suite + report.** Green test suite; report each command with its observed
  result.

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`). Runner:
`venv/bin/python -m pytest`.

Checks to run and report (`<command>: <observed result>`):

```bash
venv/bin/python -m pytest -q tests/test_assets.py
venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
bash tools/build_tailwind.sh && ls -l static/css/tailwind.css
```

Post-fix measurement (separate step): re-run the same Lighthouse mobile runs on `/` and
`/catalog`; Phase A left the "before" at home 90 / catalog 68, 393 / 836 KB.

## Delivery and rollback

- Delivery: `single-pr` on `feature/tailwind-prebuilt` (base `main` @ `574cbea`).
  Commit/push/PR/merge are user-owned and **not** part of this work unit.
- Rollback: revert the commits; restores the Play CDN script. No data, migration, or
  server behavior change — assets only.

## Progress

- [x] T1-T6 — delivered: `templates/base.html` loads no Play CDN, it links the committed
  prebuilt `/static/css/tailwind.css`; asset tests guard this.
- [ ] Lighthouse after-measurement.
- [ ] Commit / PR — user-owned, pending explicit go-ahead.

## Follow-up delivered

The v4 migration this work unit deferred (line "Out of scope: Tailwind v4 migration") was
delivered in `odd/tasks/tailwind-v4.md`: the toolchain moved to the v4.3.3 standalone binary,
the config is now CSS-first (`static/css/tailwind.src.css`, `tailwind.config.js` deleted),
and the renamed utilities are applied across the templates. The v3 pin above is historical.
