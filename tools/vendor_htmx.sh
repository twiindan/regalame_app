#!/usr/bin/env bash
# Re-vendor the self-hosted HTMX runtime. Run from the repository root.
set -euo pipefail

HTMX_VERSION="1.9.10"
DEST="static/js/htmx.min.js"

mkdir -p "$(dirname "$DEST")"
curl -fsSL "https://unpkg.com/htmx.org@${HTMX_VERSION}/dist/htmx.min.js" -o "$DEST"
