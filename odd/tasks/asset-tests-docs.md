# Asset tests, docs and duotone cleanup (findings PR 2)

Second half of the findings work for roadmap item 6, on top of #66 (merged). Closes the
non-blocking test/doc findings from the reviews of #64 and #65. The only ODD artifact here.

## Objective

The prebuilt CSS and the local SVG pipeline are verified only superficially, the duotone SVG
blobs are duplicated across templates, and two docs carry wrong or absolute references.

## Scope

In scope:

- `tests/test_assets.py`: assert (a) every Tailwind class toggled/assigned by inline JS is
  present in the generated `static/css/tailwind.css`; (b) the server actually returns
  `/static/css/tailwind.css` and `/static/css/phosphor.css` (not just that the files exist);
  (c) the duotone migration — no `<i class="ph-duotone` remains and the inline `<svg>` are
  present; (d) every icon asset exists, is non-empty, parses as SVG, and the selector's
  `mask-image` URL resolves to that same file.
- Reuse the generator's own scanner (`tools/build_phosphor_icons.py::scan_used_icons`) as the
  single source of truth instead of a second regex, loaded via `importlib` from the file path.
- `templates/macros.html`: one macro per duotone icon (gift, magnifying-glass, ticket, image,
  ghost) emitting the `<svg>` with `width="1em" height="1em"`; replace the 8 inline blobs with
  macro calls so the icon has a single source of truth.
- Docs: `odd/tasks/phosphor-svg.md` `build_phosphor_icons.sh` -> `.py`; `odd/tasks/tailwind-prebuilt.md`
  "nine baselines" -> eight; absolute local venv paths -> repo-relative in both docs.
- Regenerate the eight `editorial_off_*.html` baselines (the `width`/`height` attributes change
  the rendered SVG).

Out of scope: Tailwind v4, Amazon images, catalog document size.

## TDD mode and verification

**Mode: strict TDD on**. Runner: `venv/bin/python -m pytest`.

```bash
venv/bin/python -m pytest -q tests/test_assets.py
venv/bin/python -m pytest -q tests/test_editorial_filtering.py --editorial-update-baselines
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
```

## Delivery and rollback

`single-pr` on `feature/asset-tests-docs` (base `main` @ `cea4b8b`). Commit/push/PR/merge are
user-owned. Rollback: revert; no runtime change.

## Progress

- [x] Tests, macro, docs, baselines.
- [x] Delivered under ordinary repository policy: PR #67 (commit bb3fdd0). The native review did
      not close — the single selected lens (`review-reliability`) returned empty reviewer output
      on every attempt — so no PASS or receipt exists for this candidate.
