# Phosphor icons to local SVG (mobile performance, roadmap item 6)

Second Phase B work unit of roadmap item 6 (`seo/next-improvements-roadmap`, Engram #932),
after `odd/tasks/tailwind-prebuilt.md` (merged, PR #64). This is the only ODD planning
artifact for this work unit.

## Objective and problem

Every page loads four full Phosphor web-font stylesheets plus the glyph fonts from
`cdn.jsdelivr.net` (`@phosphor-icons/web@2.1.2`: regular, bold, fill, duotone). The fonts
are binary, so edge Brotli does not shrink them: `Phosphor-Bold.woff2` alone is ~147 KB and
`Phosphor-Fill.woff2` ~129 KB, on top of ~84 KB of weight CSS. Templates use only **47
distinct icons** out of ~9k, and every usage is a static literal class (no dynamic
construction).

Replace the font CSS/CDN with **local SVGs driven by CSS `mask`**, keeping the existing
`<i class="ph-bold ph-check">` markup unchanged.

## Why this approach (decision, resolved)

User chose option A. Rejected alternatives: rewriting all 92 usage sites as literal inline
SVG (large, churny diff), and subsetting the fonts with fonttools (keeps the font
dependency and adds a build dep).

- Single-color weights (bold, fill, regular) render through a generated
  `static/css/phosphor.css`: one `mask-image` rule per used icon, colored with
  `background-color: currentColor`, sized with `1em`.
- The **8 duotone** usages (`ph-duotone`) become **inline `<svg>`** in the templates: the
  two-tone effect (secondary layer `opacity="0.2"`) is preserved exactly without relying on
  mask alpha semantics.
- Source of truth for the SVGs: pinned `@phosphor-icons/core@2.1.1` on jsdelivr,
  `/assets/<weight>/<name>-<weight>.svg` (the `regular` weight has no suffix).

## Authorized scope and boundary

In scope:

- `tools/build_phosphor_icons.py`: pins the core version, scans `templates/**/*.html` +
  `main.py` for the used `(weight, name)` pairs, downloads each non-duotone SVG to
  `static/icons/<weight>/<name>.svg`, and generates `static/css/phosphor.css`.
- Generated, committed: `static/icons/**/*.svg` (~41 files) and `static/css/phosphor.css`.
- `templates/base.html`: replace the four `@phosphor-icons/web` CDN `<link>`s with one
  `<link rel="stylesheet" href="/static/css/phosphor.css">`.
- The 8 `ph-duotone` usages: inline `<svg>` (same visual, `fill="currentColor"`,
  `viewBox="0 0 256 256"`, `width/height 1em`).
- `tests/test_assets.py`: regression assertions.
- Regenerate the eight `editorial_off_*.html` baselines.

Out of scope: Tailwind (done), HTMX self-hosting, Amazon images, font tools.

## Tasks and acceptance

- [ ] **T1 — Regression test (RED first).** Assert the rendered home has no
  `@phosphor-icons/web` / `cdn.jsdelivr.net` reference, links `/static/css/phosphor.css`,
  that `static/icons/<weight>/<name>.svg` exists for every non-duotone used icon, and that
  `phosphor.css` contains the matching `.ph-<weight>.ph-<name>` rules.
- [ ] **T2 — Build script + generated assets.** `tools/build_phosphor_icons.py` (Python,
  pinned version) produces the icons and the CSS.
- [ ] **T3 — base.html swap.** Remove the four CDN links; add the local stylesheet.
- [ ] **T4 — Duotone to inline SVG.** The 8 sites listed below; keep the existing Tailwind
  classes for size/color/margin.
- [ ] **T5 — Baselines.** Regenerate the eight; confirm the diff is only the head assets and
  the duotone `<i>` -> `<svg>` swaps.
- [ ] **T6 — Full suite + report** with observed results.

## Duotone sites (inline SVG)

- `templates/group.html` — ticket
- `templates/blog_post.html` — ghost
- `templates/dashboard.html` — gift
- `templates/inspiration.html` — magnifying-glass
- `templates/partials/wish_item.html` — gift
- `templates/partials/catalog_results.html` — image, magnifying-glass
- `templates/blog_index.html` — gift

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`). Runner:
`venv/bin/python -m pytest`.

```bash
venv/bin/python -m pytest -q tests/test_assets.py
venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
venv/bin/python tools/build_phosphor_icons.py && ls -1 static/icons/*/ | wc -l
```

Post-fix measurement (separate step): same mobile Lighthouse A/B as the Tailwind unit
(home + catalog), against `main` @ `8fcd56f`.

## Delivery and rollback

- Delivery: `single-pr` on `feature/phosphor-svg` (base `main` @ `8fcd56f`).
  Commit/push/PR/merge are user-owned.
- Rollback: revert the commits; restores the CDN font stylesheets. Assets only.

## Progress

- [ ] T1-T6.
- [ ] Lighthouse after-measurement.
- [ ] Commit / PR — user-owned.
