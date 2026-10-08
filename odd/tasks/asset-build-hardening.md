# Hardening the asset build tools (Tailwind + Phosphor)

Follow-up work unit for roadmap item 6, resolving the non-blocking build-tooling findings from
the native reviews of PR #64 (`odd/tasks/tailwind-prebuilt.md`) and PR #65
(`odd/tasks/phosphor-svg.md`). This is the only ODD planning artifact for this work unit.

## Objective and problem

Both asset builders download pinned upstream artifacts and then execute or install them with
weak integrity and portability guarantees:

- `tools/build_tailwind.sh` downloads the Tailwind standalone binary and runs it with only a
  release tag pinned (no hash), a hardcoded `tailwindcss-macos-arm64` asset (so it cannot run on
  Linux or Intel macOS, and its cache path is keyed only by version), and it never `cd`s to the
  repository root even though `tailwind.config.js` declares **relative** content globs.
- `tools/build_phosphor_icons.py` validates a download with a bare `b"<svg"` substring test and
  overwrites committed assets in place, so a truncated response can be written and a mid-run
  failure leaves new SVGs paired with a stale `phosphor.css`.

**Acceptance is artifact-neutrality**: after this change, re-running both builders must leave
`static/` byte-identical to what is committed. PR #1 touches only the two tools.

## Findings addressed

Tailwind (PR #64): unverified binary download (R1-unverified-binary-download, R3-003), hardcoded
asset / no platform detection (R2-1, R3-004, R4-2), cache path keyed only by version (R2-4),
missing `cd` to repo root (R3-002), no retry/timeout (R4-3).
Phosphor (PR #65): weak integrity check and non-atomic writes (R4-B, R3-4).

## Authorized scope and boundary

In scope, `tools/build_tailwind.sh`:

- Resolve the target asset from `uname -s` / `uname -m` (`Darwin/arm64` -> `macos-arm64`,
  `Darwin/x86_64` -> `macos-x64`, `Linux/x86_64` -> `linux-x64`), warn and continue on a
  best-effort name for other platforms.
- **Verify SHA-256** of the downloaded binary against a pinned map before executing it; a
  mismatched or already-corrupted cached binary must be re-downloaded and re-verified.
- Cache path includes the asset name: `tools/.bin/tailwindcss-<version>-<asset>`.
- `cd` to the repository root before invoking the binary.
- Retry the download a bounded number of times with connect/overall timeouts.

In scope, `tools/build_phosphor_icons.py`:

- Validate every downloaded SVG by parsing it (`xml.etree.ElementTree`) and requiring a non-empty
  `<svg>` root; a parse failure aborts before anything is written.
- **Stage then commit**: download and validate everything into a temp directory, then write the
  icons and the stylesheet; a failure during download must leave the working tree untouched.

Out of scope (PR 2 of the findings work): tests, docs, the duotone Jinja macro, inline-SVG
sizing.

## Pinned hashes (TOFU)

The v3.4.17 release publishes no signed checksums (the GitHub API `digest` field is `null`), so
these are the SHA-256 of the artifacts fetched over HTTPS from the official release at
implementation time; they make the build reproducible and detect any later replacement:

- `tailwindcss-macos-arm64` `a1d0c7985759accca0bf12e51ac1dcbf0f6cf2fffb62e6e0f62d091c477a10a3`
- `tailwindcss-macos-x64` `6cbdad74be776c087ffa5e9a057512c54898f9fe8828d3362212dfe32fc933a3`
- `tailwindcss-linux-x64` `7d24f7fa191d2193b78cd5f5a42a6093e14409521908529f42d80b11fde1f1d4`

## Tasks and acceptance

- [x] **T1 — Tailwind script**: platform resolution, pinned-hash verification (including a
      corrupted-cache re-download), asset-keyed cache, `cd` to root, bounded retry/timeout.
- [x] **T2 — Phosphor tool**: `ElementTree` well-formedness validation and stage-then-commit.
- [x] **T3 — Artifact neutrality**: run both builders and confirm `git status --short static/`
      is clean (the committed artifacts reproduce byte-for-byte).
- [x] **T4 — Full suite green** with observed results.

## TDD mode and verification checks

**Mode: strict TDD on** (`openspec/config.yaml`). Runner:
`/Users/toni.robres/Pycharmprojects/regalame_gemini3/venv/bin/python -m pytest`.

```bash
bash tools/build_tailwind.sh && venv/bin/python tools/build_phosphor_icons.py
git status --short static/          # must be empty (artifact-neutral)
venv/bin/python -m pytest -q --ignore=tests/test_e2e.py
sha256sum static/css/tailwind.css static/css/phosphor.css   # record before/after
```

## Delivery and rollback

- Delivery: `single-pr` on `feature/asset-build-hardening` (base `main` @ `83a5568`).
  Commit/push/PR/merge are user-owned.
- Rollback: revert the commits; the tools return to the previous versions. No runtime or asset
  behavior change.

## Progress

- [x] T1-T4.
- [x] Delivered under ordinary repository policy: PR #66 (commit 604b87e). The native review did
      not close — 3 of 4 lenses returned empty reviewer output on the initial batch and on the
      bounded relaunch — so no PASS or receipt exists for this candidate.
- [x] Extra finding folded in: the committed `static/css/tailwind.css` carried a dead
      `.ease-out` rule (-60 B) and was not reproducible; it is regenerated so re-running both
      builders leaves `static/` byte-identical.
