# Amigo Invisible SEO Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a repeatable GSC report CLI (roadmap item 4) and a data-driven Christmas "amigo invisible" content campaign (on-page, linking, 3 informational posts, 2 audience posts).

**Architecture:** Single local CLI module `tools/gsc_report.py` (auth -> fetch -> pure report builders -> markdown emitter). Web changes are additive template/config edits following existing mechanisms (`blog_config` criteria, `extra_schema` block, organizer aside).

**Tech Stack:** Python 3 + google-auth + requests (local only, `requirements-search-console.txt`), FastAPI + Jinja2 + pytest (web).

**Working branch:** `feature/amigo-invisible-seo-campaign` (base `main` @ `917b4e7`). ODD doc: `odd/tasks/amigo-invisible-seo-campaign.md` (update it after each task). Spec: `docs/superpowers/specs/2026-11-02-amigo-invisible-seo-campaign-design.md`. Runner: `venv/bin/python -m pytest`. Strict TDD is ON: observe RED before every implementation step. UI copy: neutral Spanish, no invented numbers or superlative claims. Conventional Commits, no AI attribution. Untracked `sample.json` / `sample.curacion-worktree.json` are never touched. Golden baselines regenerate only for intended surface changes (`venv/bin/python -m pytest tests/test_editorial_filtering.py --editorial-update-baselines`, then diff must show ONLY intended blocks).

**Known environmental facts:** `/amigo-invisible` has NO golden baseline (safe to edit). `templates/blog_post.html:62` hard-codes the aside to `regalos-amigo-invisible-10-euros` (Task 9 generalizes this). `test_seo_landings.py:19` asserts the exact organizer title. `services.get_blog_post_detail` (services.py:258) supports `criteria.items`, `criteria.category`, `criteria.max_price`, `criteria.limit` — no multi-category yet (Task 12 adds it).

---

### Task 1: Local deps, gitignore, and the GSC setup guide

**Files:**
- Modify: `requirements-search-console.txt`
- Modify: `.gitignore`
- Create: `docs/gsc-setup-guide.md`

- [ ] **Step 1: Add `requests` to the local-only requirements**

`requirements-search-console.txt` becomes:

```
# Local CLI only; do not install into the production application environment.
google-auth==2.60.0
google-auth-oauthlib==1.5.0
requests-oauthlib==2.0.0
oauthlib==4.0.0
requests==2.32.3
```

- [ ] **Step 2: Ignore secrets and reports**

Append to `.gitignore`:

```
# GSC local tooling (never commit credentials or generated reports)
tools/gsc_service_account.json
tools/reports/
```

- [ ] **Step 3: Write the setup guide**

Create `docs/gsc-setup-guide.md` with exactly this content (neutral English, real steps):

```markdown
# Search Console report tool — one-time setup

`tools/gsc_report.py` reads your Search Console data via the API. It runs on
your machine only; nothing ships to production. Two auth options.

## Option A — Service account (recommended, never expires)

1. https://console.cloud.google.com/ -> create (or pick) a project.
2. APIs & Services -> Library -> enable **Search Console API**.
3. IAM & Admin -> Service Accounts -> Create service account (no roles needed).
4. Open the account -> Keys -> Add key -> JSON -> save as
   `tools/gsc_service_account.json` (this path is gitignored).
5. Search Console (https://search.google.com/search-console) -> Settings ->
   Users and permissions -> Add user -> paste the service account email
   (ends in `.iam.gserviceaccount.com`) -> permission **Owner** (required for
   full data).
6. Install local deps once: `venv/bin/python -m pip install -r requirements-search-console.txt`
7. Run: `venv/bin/python tools/gsc_report.py --days 90`

## Option B — OAuth (fallback)

Refresh tokens for OAuth apps in "Testing" mode expire after 7 days; prefer
Option A. If you need OAuth:

1. Same GCP project -> APIs & Services -> OAuth consent screen (External,
   Testing) -> add yourself as test user.
2. Credentials -> Create credentials -> OAuth client ID -> Desktop app ->
   download JSON to `tools/gsc_client_secret.json` (gitignored).
3. Run `venv/bin/python tools/gsc_report.py --oauth` and follow the browser
   consent. The token caches at `~/.config/regalame/gsc_token.json`.

## Notes

- `--site` defaults to `https://regalame.app/`. If your property is a
  **domain** property, pass `--site sc-domain:regalame.app`. Check the
  property card in Search Console to see which one you have.
- Reports print to stdout; use `--out tools/reports/gsc-YYYY-MM-DD.md` to
  save (gitignored).
```

- [ ] **Step 4: Verify the tool has no prod deps leaking**

Run: `venv/bin/python -m pip install -r requirements-search-console.txt`
Expected: installs cleanly into the dev venv.

- [ ] **Step 5: Commit**

```bash
git add requirements-search-console.txt .gitignore docs/gsc-setup-guide.md
git commit -m "chore(seo): add GSC setup guide, local deps and secret ignores"
```

---

### Task 2: Row aggregation and seasonal matcher (pure)

**Files:**
- Create: `tools/gsc_report.py`
- Create: `tests/test_gsc_report.py`

`tools/gsc_report.py` starts with the pure layer only (no I/O imports).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_gsc_report.py`:

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from gsc_report import aggregate_by, is_seasonal  # noqa: E402


def _row(query, page="https://regalame.app/", clicks=0, impressions=1, position=10.0):
    return {
        "query": query,
        "page": page,
        "clicks": clicks,
        "impressions": impressions,
        "position": position,
    }


def test_is_seasonal_matches_stems_case_insensitively():
    assert is_seasonal("Amigo Invisible online")
    assert is_seasonal("regalos para niños")
    assert is_seasonal("IDEAS DE NAVIDAD")
    assert not is_seasonal("minecraft skins")


def test_aggregate_by_query_sums_and_weights():
    rows = [
        _row("amigo invisible", page="/a", clicks=2, impressions=100, position=5.0),
        _row("amigo invisible", page="/b", clicks=1, impressions=100, position=7.0),
        _row("otra cosa", page="/a", clicks=0, impressions=10, position=20.0),
    ]
    agg = {a["query"]: a for a in aggregate_by(rows, "query")}
    mine = agg["amigo invisible"]
    assert mine["clicks"] == 3
    assert mine["impressions"] == 200
    assert mine["ctr"] == 0.015
    assert mine["position"] == 6.0  # weighted by equal impressions


def test_aggregate_by_zero_impressions_is_safe():
    agg = aggregate_by([_row("q", clicks=0, impressions=0, position=0.0)], "query")
    assert agg[0]["position"] == 0.0
    assert agg[0]["ctr"] == 0.0
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: FAIL (ModuleNotFoundError: gsc_report).

- [ ] **Step 3: Implement the pure layer**

Create `tools/gsc_report.py`:

```python
"""Google Search Console report CLI. Local tooling only — never imported by the app.

Layering: pure report builders (no I/O) -> auth/fetch -> CLI. Tests cover the
pure layer with fixtures; auth/fetch run against a fake transport.
"""

SEASONAL_STEMS = ("amigo invisible", "regalo", "navidad")


def is_seasonal(query, stems=SEASONAL_STEMS):
    """Case-insensitive substring match on the configured stems."""
    q = query.lower()
    return any(stem in q for stem in stems)


def _weighted_average(rows, key):
    total = sum(r["impressions"] for r in rows)
    if total == 0:
        return 0.0
    return sum(r[key] * r["impressions"] for r in rows) / total


def aggregate_by(rows, key):
    """Aggregate rows by 'query' or 'page': sums, ctr, impression-weighted position."""
    grouped = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    result = []
    for value, group in grouped.items():
        clicks = sum(r["clicks"] for r in group)
        impressions = sum(r["impressions"] for r in group)
        result.append({
            key: value,
            "clicks": clicks,
            "impressions": impressions,
            "ctr": (clicks / impressions) if impressions else 0.0,
            "position": _weighted_average(group, "position"),
        })
    return result
```

- [ ] **Step 4: Run to verify GREEN**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/gsc_report.py tests/test_gsc_report.py
git commit -m "feat(seo): pure GSC row aggregation and seasonal matcher"
```

---

### Task 3: The four report views (pure)

**Files:**
- Modify: `tools/gsc_report.py`
- Modify: `tests/test_gsc_report.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gsc_report.py`:

```python
from gsc_report import build_low_ctr, build_opportunities, build_per_url, build_top_queries  # noqa: E402


def _mix():
    return [
        _row("amigo invisible online", clicks=1, impressions=50, position=8.0),
        _row("amigo invisible", clicks=0, impressions=30, position=12.0),
        _row("regalos navidad", clicks=5, impressions=200, position=3.0),
        _row("minecraft", clicks=0, impressions=90, position=9.0),
        _row("amigo invisible app", clicks=0, impressions=15, position=2.0),
        _row("regalo barato", clicks=0, impressions=12, position=6.5),
    ]


def test_top_queries_filters_non_seasonal_and_sorts_by_impressions():
    top = build_top_queries(_mix())
    assert [t["query"] for t in top][:3] == ["regalos navidad", "amigo invisible online", "amigo invisible"]
    assert all("minecraft" != t["query"] for t in top)


def test_opportunities_window_is_half_open():
    hits = build_opportunities(_mix(), min_impressions=10)
    queries = [h["query"] for h in hits]
    assert "amigo invisible" in queries        # position 12
    assert "amigo invisible online" in queries  # position 8
    assert "regalos navidad" not in queries     # position 3 (< 5)
    assert "amigo invisible app" not in queries  # position 2 (< 5)


def test_low_ctr_flags_good_position_low_clicks():
    hits = build_low_ctr(_mix())
    queries = [h["query"] for h in hits]
    assert "amigo invisible app" in queries     # position 2, ctr 0
    assert "minecraft" not in queries           # position 9 > 6, excluded


def test_low_ctr_respects_clicks_not_stems():
    # 5/200 = 0.025 < 0.03 but has clicks; keep the view honest: any query under
    # the ctr threshold at good position is a candidate. "regalos navidad" HAS
    # 5 clicks so it still appears; assert exactly that.
    hits = build_low_ctr(_mix())
    queries = [h["query"] for h in hits]
    assert "regalos navidad" in queries


def test_per_url_aggregates_pages():
    rows = [
        _row("a", page="/p1", clicks=1, impressions=10, position=4.0),
        _row("b", page="/p1", clicks=1, impressions=30, position=8.0),
        _row("c", page="/p2", clicks=0, impressions=5, position=11.0),
    ]
    agg = {a["page"]: a for a in build_per_url(rows)}
    assert agg["/p1"]["impressions"] == 40
    assert agg["/p1"]["clicks"] == 2
    assert round(agg["/p1"]["position"], 2) == 7.0
    assert agg["/p2"]["impressions"] == 5


def test_views_empty_rows_return_empty_lists():
    assert build_top_queries([]) == []
    assert build_opportunities([]) == []
    assert build_low_ctr([]) == []
    assert build_per_url([]) == []
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: FAIL (ImportError: cannot import view builders).

- [ ] **Step 3: Implement the view builders**

Append to `tools/gsc_report.py`:

```python
def build_top_queries(rows, stems=SEASONAL_STEMS, limit=50):
    """V1: seasonal queries aggregated per query, sorted by impressions."""
    seasonal = [r for r in rows if is_seasonal(r["query"], stems)]
    agg = aggregate_by(seasonal, "query")
    agg.sort(key=lambda a: (-a["impressions"], a["query"]))
    return agg[:limit]


def build_opportunities(rows, min_impressions=10, low=5.0, high=20.0):
    """V2: (query, page) rows with average position in [low, high)."""
    hits = [
        r for r in rows
        if low <= r["position"] < high and r["impressions"] >= min_impressions
    ]
    hits.sort(key=lambda r: (-r["impressions"], r["position"], r["query"]))
    return hits


def build_low_ctr(rows, max_position=6.0, ctr_threshold=0.03, min_impressions=10):
    """V3: queries ranking well (position <= max_position) with ctr under threshold."""
    agg = aggregate_by(rows, "query")
    hits = [
        a for a in agg
        if a["position"] <= max_position
        and a["ctr"] < ctr_threshold
        and a["impressions"] >= min_impressions
    ]
    hits.sort(key=lambda a: (-a["impressions"], a["position"]))
    return hits


def build_per_url(rows):
    """V4: per-page aggregates, sorted by impressions."""
    agg = aggregate_by(rows, "page")
    agg.sort(key=lambda a: (-a["impressions"], a["page"]))
    return agg
```

- [ ] **Step 4: Run to verify GREEN**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: PASS (9 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/gsc_report.py tests/test_gsc_report.py
git commit -m "feat(seo): GSC report views (top queries, opportunities, low ctr, per-url)"
```

---

### Task 4: Markdown emitter (pure)

**Files:**
- Modify: `tools/gsc_report.py`
- Modify: `tests/test_gsc_report.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_gsc_report.py`:

```python
from gsc_report import render_markdown  # noqa: E402


def test_render_markdown_contains_views_and_no_data_messages():
    md = render_markdown([], site="https://regalame.app/", start="2026-08-05", end="2026-11-03")
    assert "GSC report — https://regalame.app/ (2026-08-05 .. 2026-11-03)" in md
    assert md.count("No data") == 4  # one per view
    assert "V1" in md and "V2" in md and "V3" in md and "V4" in md


def test_render_markdown_renders_rows_with_numbers():
    rows = [_row("amigo invisible", page="/a", clicks=2, impressions=100, position=5.0)]
    md = render_markdown(rows, site="s", start="d1", end="d2")
    assert "amigo invisible" in md
    assert "100" in md
    assert "/a" in md
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: FAIL (ImportError: render_markdown).

- [ ] **Step 3: Implement the emitter**

Append to `tools/gsc_report.py`:

```python
def _table(rows, headers):
    if not rows:
        return "_No data_\n"
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        lines.append("| " + " | ".join(str(r[h]) for h in headers) + " |")
    return "\n".join(lines) + "\n"


def render_markdown(rows, site, start, end, stems=SEASONAL_STEMS,
                    min_impressions=10, ctr_threshold=0.03, limit=50):
    out = [f"# GSC report — {site} ({start} .. {end})\n"]
    out.append("## V1 — Top seasonal queries\n")
    out.append(_table(
        build_top_queries(rows, stems, limit),
        ["query", "clicks", "impressions", "ctr", "position"],
    ))
    out.append("## V2 — Opportunities (position 5-20)\n")
    out.append(_table(
        build_opportunities(rows, min_impressions),
        ["query", "page", "clicks", "impressions", "position"],
    ))
    out.append("## V3 — Low CTR at good position\n")
    out.append(_table(
        build_low_ctr(rows, ctr_threshold=ctr_threshold, min_impressions=min_impressions),
        ["query", "clicks", "impressions", "ctr", "position"],
    ))
    out.append("## V4 — Per URL\n")
    out.append(_table(
        build_per_url(rows),
        ["page", "clicks", "impressions", "ctr", "position"],
    ))
    return "\n".join(out)
```

- [ ] **Step 4: Run to verify GREEN**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: PASS (11 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/gsc_report.py tests/test_gsc_report.py
git commit -m "feat(seo): markdown emitter for GSC report"
```

---

### Task 5: Service-account auth and paginated fetch (fake transport)

**Files:**
- Modify: `tools/gsc_report.py`
- Modify: `tests/test_gsc_report.py`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_gsc_report.py`:

```python
import pytest  # noqa: E402

from gsc_report import fetch_rows  # noqa: E402


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _FakeTransport:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    def post(self, url, json=None):
        self.calls.append((url, json))
        return _FakeResponse(self.pages.pop(0))


def test_fetch_rows_paginates_until_short_page():
    page1 = {"rows": [
        {"keys": ["amigo invisible", "/a"], "clicks": 1, "impressions": 10, "ctr": 0.1, "position": 5.0},
    ] * 2}
    page2 = {"rows": [
        {"keys": ["regalo", "/b"], "clicks": 0, "impressions": 3, "ctr": 0.0, "position": 9.0},
    ]}
    transport = _FakeTransport([page1, page2, {"rows": []}])
    rows = fetch_rows("https://regalame.app/", credentials=object(), days=90,
                      country="es", transport=transport, page_size=2)
    assert [r["query"] for r in rows] == ["amigo invisible", "amigo invisible", "regalo"]
    assert rows[0]["page"] == "/a"
    assert len(transport.calls) == 3
    first_url, first_body = transport.calls[0]
    assert "searchconsole.googleapis.com" in first_url
    assert "sites/https%3A%2F%2Fregalame.app%2F" in first_url
    assert first_body["dimensions"] == ["query", "page"]
    assert first_body["startDate"] > first_body["endDate"] is False  # sanity: start < end
    assert first_body["dimensionFilterGroups"][0]["filters"][0]["expression"] == "es"


def test_fetch_rows_retries_on_429_then_succeeds(monkeypatch):
    class Flaky:
        def __init__(self):
            self.calls = 0

        def post(self, url, json=None):
            self.calls += 1
            if self.calls == 1:
                return _FakeResponse({}, status=429)
            return _FakeResponse({"rows": [
                {"keys": ["q", "/p"], "clicks": 0, "impressions": 1, "ctr": 0.0, "position": 1.0},
            ]})

    sleeps = []
    transport = Flaky()
    rows = fetch_rows("https://regalame.app/", credentials=object(), days=7,
                      country="es", transport=transport, sleep=sleeps.append)
    assert len(rows) == 1
    assert sleeps == [1, 2, 4]


def test_fetch_rows_empty_property_returns_empty_list():
    transport = _FakeTransport([{}])
    assert fetch_rows("s", credentials=object(), days=7, country="es",
                      transport=transport) == []
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: FAIL (ImportError: fetch_rows).

- [ ] **Step 3: Implement auth + fetch**

Append to `tools/gsc_report.py`:

```python
import os  # noqa: E402
import time as time_module  # noqa: E402
from datetime import date, timedelta  # noqa: E402
from urllib.parse import quote  # noqa: E402

API_ROOT = "https://searchconsole.googleapis.com/webmasters/v3/sites"
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
DEFAULT_SA_PATH = os.path.join(os.path.dirname(__file__), "gsc_service_account.json")

_SETUP_HINT = (
    "No service account found at {path}.\n"
    "Follow docs/gsc-setup-guide.md (Option A, ~10 minutes) and retry."
)


def load_credentials(path=DEFAULT_SA_PATH):
    """Load service-account credentials; exit with setup guidance when missing."""
    if not os.path.exists(path):
        raise SystemExit(_SETUP_HINT.format(path=path))
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)


def load_oauth_credentials(client_secret_path=None, token_path=None):
    """Fallback: installed-app OAuth flow. Testing-mode tokens expire in 7 days."""
    from pathlib import Path
    client_secret_path = client_secret_path or os.path.join(
        os.path.dirname(__file__), "gsc_client_secret.json")
    token_path = Path(token_path or Path.home() / ".config/regalame/gsc_token.json")
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
    token_path.parent.mkdir(parents=True, exist_ok=True)
    credentials = flow.run_local_server(port=0)
    token_path.write_text(credentials.to_json())
    return credentials


def _credentials_from_token(token_path):
    from google.oauth2.credentials import Credentials
    return Credentials.from_authorized_user_file(str(token_path), SCOPES)


def _authed_session(credentials):
    from google.auth.transport.requests import AuthorizedSession
    return AuthorizedSession(credentials)


def fetch_rows(site_url, credentials, days=90, country="es",
               transport=None, page_size=25000, sleep=time_module.sleep):
    """Fetch query x page rows for the last `days` days, filtered by country.

    `transport` is injectable for tests; production uses AuthorizedSession.
    Retries 429/5xx with 1/2/4s backoff (3 attempts), then raises.
    """
    end = date.today()
    start = end - timedelta(days=days)
    url = f"{API_ROOT}/{quote(site_url, safe='')}/searchAnalytics/query"
    session = transport if transport is not None else _authed_session(credentials)
    rows, start_row = [], 0
    while True:
        payload = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["query", "page"],
            "rowLimit": page_size,
            "startRow": start_row,
            "dimensionFilterGroups": [{
                "groupType": "and",
                "filters": [{"dimension": "country", "operator": "equals",
                             "expression": country}],
            }],
        }
        response = None
        for attempt in range(3):
            response = session.post(url, json=payload)
            if response.status_code not in (429, 500, 502, 503):
                break
            if attempt < 2:
                sleep(2 ** attempt)
        response.raise_for_status()
        data = response.json()
        batch = data.get("rows", [])
        for entry in batch:
            keys = entry["keys"]
            rows.append({
                "query": keys[0], "page": keys[1],
                "clicks": entry["clicks"], "impressions": entry["impressions"],
                "position": entry["position"],
            })
        if len(batch) < page_size:
            return rows
        start_row += page_size
```

- [ ] **Step 4: Run to verify GREEN**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/gsc_report.py tests/test_gsc_report.py
git commit -m "feat(seo): GSC service-account auth and paginated fetch with backoff"
```

---

### Task 6: CLI entrypoint

**Files:**
- Modify: `tools/gsc_report.py`
- Modify: `tests/test_gsc_report.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_gsc_report.py`:

```python
from gsc_report import main  # noqa: E402


def test_main_writes_report_and_honors_flags(tmp_path, monkeypatch):
    out = tmp_path / "report.md"
    transport = _FakeTransport([{"rows": [
        {"keys": ["amigo invisible", "/amigo-invisible"],
         "clicks": 3, "impressions": 40, "ctr": 0.075, "position": 6.0},
    ]}])
    code = main([
        "--site", "https://regalame.app/",
        "--days", "30",
        "--out", str(out),
    ], transport=transport, credentials=object())
    assert code == 0
    text = out.read_text()
    assert "V1 — Top seasonal queries" in text
    assert "amigo invisible" in text
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: FAIL (ImportError: main).

- [ ] **Step 3: Implement main()**

Append to `tools/gsc_report.py`:

```python
def main(argv=None, transport=None, credentials=None):
    """CLI entry. `transport`/`credentials` are test injection points."""
    import argparse
    parser = argparse.ArgumentParser(description="Search Console report (local CLI).")
    parser.add_argument("--site", default=os.environ.get(
        "GSC_SITE_URL", "https://regalame.app/"))
    parser.add_argument("--days", type=int, default=90)
    parser.add_argument("--country", default="es")
    parser.add_argument("--min-impressions", type=int, default=10)
    parser.add_argument("--ctr-threshold", type=float, default=0.03)
    parser.add_argument("--stems", default=",".join(SEASONAL_STEMS))
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--out", default=None)
    parser.add_argument("--oauth", action="store_true",
                        help="Use OAuth flow instead of the service account.")
    args = parser.parse_args(argv)

    if credentials is None:
        if args.oauth:
            token_path = os.path.expanduser("~/.config/regalame/gsc_token.json")
            credentials = (_credentials_from_token(token_path)
                           if os.path.exists(token_path)
                           else load_oauth_credentials())
        else:
            credentials = load_credentials()

    rows = fetch_rows(args.site, credentials, days=args.days,
                      country=args.country, transport=transport)
    stems = tuple(s.strip().lower() for s in args.stems.split(",") if s.strip())
    report = render_markdown(rows, site=args.site,
                             start=(date.today() - timedelta(days=args.days)).isoformat(),
                             end=date.today().isoformat(),
                             stems=stems, min_impressions=args.min_impressions,
                             ctr_threshold=args.ctr_threshold, limit=args.limit)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(report)
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run to verify GREEN, then the whole file suite**

Run: `venv/bin/python -m pytest tests/test_gsc_report.py -v`
Expected: PASS (15 tests).

- [ ] **Step 5: Commit**

```bash
git add tools/gsc_report.py tests/test_gsc_report.py
git commit -m "feat(seo): GSC report CLI entrypoint with flags"
```

---

### Task 7: Baseline run and data checkpoint (WITH THE USER)

This task needs the user's GCP service account (docs/gsc-setup-guide.md, Option A). No code changes.

- [ ] **Step 1: Hand the guide to the user and wait for setup**

Ask the user to follow `docs/gsc-setup-guide.md` Option A. Wait for confirmation that `tools/gsc_service_account.json` exists.

- [ ] **Step 2: Run the baseline**

Run: `venv/bin/python tools/gsc_report.py --days 90 --out tools/reports/gsc-baseline-$(date +%F).md`
Expected: exit 0; report file exists. If it exits with the setup hint, go back to Step 1.

- [ ] **Step 3: Review findings WITH the user and record targets**

Read the report. Together decide: the final title/description/H1 wording for `/amigo-invisible` (default: keep current unless data shows better terms), and the 5 information/audience post titles. Record them in `odd/tasks/amigo-invisible-seo-campaign.md` under a new `## T4 targets` heading. Do NOT proceed to Task 8 without this recorded.

- [ ] **Step 4: Update ODD doc progress**

Mark T4 progress in `odd/tasks/amigo-invisible-seo-campaign.md` with the report filename and the decision summary.

---

### Task 8: On-page tuning of `/amigo-invisible`

**Files:**
- Modify: `templates/amigo_invisible.html`
- Modify: `tests/test_seo_landings.py`

The defaults below assume Task 7 kept the current title (check `## T4 targets` first; if it recorded different strings, use those in the assertions and template).

- [ ] **Step 1: Write the failing tests**

In `tests/test_seo_landings.py`, modify `test_landings_have_distinct_wishlist_and_organizer_intent` assertions to the recorded title, add an `/ideas` link assertion, and append the FAQ test:

```python
def test_organizer_landing_links_category_ideas(client):
    soup = page(client, "/amigo-invisible")
    assert soup.main.find("a", href="/ideas")


def test_organizer_landing_has_visible_faq_and_faqpage_schema(client):
    soup = page(client, "/amigo-invisible")
    faq_heading = soup.main.find("h2", string="Preguntas frecuentes")
    assert faq_heading
    questions = [h3.get_text(strip=True) for h3 in faq_heading.find_next("div").find_all("h3")]
    assert len(questions) == 3

    schemas = _json_ld(soup)  # existing helper at tests/test_seo_landings.py:303
    faq = next(item for item in schemas if item.get("@type") == "FAQPage")
    names = [q["name"] for q in faq["mainEntity"]]
    for question in questions:
        assert question in names
```

(Reuse the file's existing `_json_ld(soup)` helper — do not re-implement JSON parsing.)

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py -v -k "faq or organizer"`
Expected: FAIL (no FAQ section, no FAQPage schema on the organizer page).

- [ ] **Step 3: Implement the FAQ section and schema**

In `templates/amigo_invisible.html`, before the closing `</div>` of the content block, add:

```html
    <section class="glass-panel rounded-2xl p-8">
        <h2 class="text-2xl font-bold mb-4">Preguntas frecuentes</h2>
        <div class="space-y-6 text-gray-300">
            <div>
                <h3 class="text-lg font-semibold text-gray-200 mb-2">¿Es gratis organizar el amigo invisible?</h3>
                <p>Sí. Crear un grupo, invitar participantes y realizar el sorteo es gratuito.</p>
            </div>
            <div>
                <h3 class="text-lg font-semibold text-gray-200 mb-2">¿Cada participante necesita una cuenta?</h3>
                <p>Sí. Para unirse al grupo y consultar a quién le toca regalar, cada persona inicia sesión con su cuenta.</p>
            </div>
            <div>
                <h3 class="text-lg font-semibold text-gray-200 mb-2">¿Cómo invito a mi grupo?</h3>
                <p>Comparte el enlace de invitación por WhatsApp o email. Cada persona entra con el enlace y se une con su cuenta.</p>
            </div>
        </div>
    </section>
```

In the same template, inside the "Ideas para los regalos de Navidad" section, extend the existing link row with a category-ideas anchor:

```html
        <div class="flex flex-wrap gap-4">
            <a href="/" class="text-pink-300 hover:text-white underline">Crear mi lista de regalos</a>
            <a href="/blog/regalos-amigo-invisible-10-euros" class="text-pink-300 hover:text-white underline">Ideas de regalos de amigo invisible por menos de 10 €</a>
            <a href="/ideas" class="text-pink-300 hover:text-white underline">Ideas de regalos por categoría</a>
        </div>
```

At the top of the same file (after the description block), add the schema block:

```html
{% block extra_schema %}
<script type="application/ld+json">
{{ {
    "@context": "https://schema.org",
    "@type": "FAQPage",
    "mainEntity": [
        {"@type": "Question", "name": "¿Es gratis organizar el amigo invisible?",
         "acceptedAnswer": {"@type": "Answer", "text": "Sí. Crear un grupo, invitar participantes y realizar el sorteo es gratuito."}},
        {"@type": "Question", "name": "¿Cada participante necesita una cuenta?",
         "acceptedAnswer": {"@type": "Answer", "text": "Sí. Para unirse al grupo y consultar a quién le toca regalar, cada persona inicia sesión con su cuenta."}},
        {"@type": "Question", "name": "¿Cómo invito a mi grupo?",
         "acceptedAnswer": {"@type": "Answer", "text": "Comparte el enlace de invitación por WhatsApp o email. Cada persona entra con el enlace y se une con su cuenta."}}
    ]
} | tojson }}
</script>
{% endblock %}
```

- [ ] **Step 4: Run to verify GREEN and no regressions**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py -v`
Expected: PASS. Update `test_landings_have_distinct_wishlist_and_organizer_intent` title assertion ONLY if Task 7 recorded a new title.

- [ ] **Step 5: Commit**

```bash
git add templates/amigo_invisible.html tests/test_seo_landings.py
git commit -m "feat(seo): FAQ section and FAQPage schema on organizer landing"
```

---

### Task 9: Generalize the organizer aside with a post flag

**Files:**
- Modify: `templates/blog_post.html:62`
- Modify: `blog_config.py` (add `"organizer_aside": True` to `regalos-amigo-invisible-10-euros`)
- Modify: `tests/test_seo_landings.py` (rewrite `test_only_relevant_blog_post_links_to_organizer`)

- [ ] **Step 1: Write the failing test**

Replace `test_only_relevant_blog_post_links_to_organizer` AND its `@pytest.mark.parametrize` decorator (line ~73-77) with:

```python
def test_organizer_aside_matches_config_flag(client):
    from blog_config import BLOG_POSTS
    for post in BLOG_POSTS:
        soup = page(client, f"/blog/{post['slug']}")
        links = soup.main.find_all("a", href="/amigo-invisible")
        if post.get("organizer_aside"):
            assert links, post["slug"]
        else:
            assert not links, post["slug"]
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py -v -k aside`
Expected: FAIL (no post has `organizer_aside` yet, but the 10-euros page currently renders the aside -> assertion mismatch).

- [ ] **Step 3: Implement flag-driven aside**

In `blog_config.py`, add the flag to the 10-euros post entry:

```python
        "criteria": {
            "max_price": 10.0
        },
        "organizer_aside": True,
        "hero_image": None
```

In `templates/blog_post.html`, replace line 62's condition `{% if post.slug == 'regalos-amigo-invisible-10-euros' %}` with:

```html
{% if post.organizer_aside %}
```

- [ ] **Step 4: Run to verify GREEN including the blog golden baseline**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py tests/test_editorial_filtering.py -v`
Expected: PASS — `editorial_off_blog.html` stays byte-identical because the 10-euros post still renders the aside.

- [ ] **Step 5: Commit**

```bash
git add blog_config.py templates/blog_post.html tests/test_seo_landings.py
git commit -m "refactor(blog): drive organizer aside from a post flag"
```

---

### Task 10: Guide sections in blog posts (text-only content support)

**Files:**
- Modify: `templates/blog_post.html`
- Modify: `tests/test_seo_landings.py` (or a focused new test file `tests/test_blog_guide_sections.py`)

- [ ] **Step 1: Write the failing test**

Create `tests/test_blog_guide_sections.py` (the `client` fixture already exists in `tests/conftest.py` — take it as a parameter, exactly like `tests/test_christmas_guide.py` does):

```python
def test_post_with_guide_renders_sections_and_headings(client):
    from blog_config import BLOG_POSTS
    BLOG_POSTS.append({
        "slug": "guide-fixture",
        "title": "Guía fixture",
        "description": "Post de prueba",
        "guide": [
            {"heading": "Sección uno", "paragraphs": ["Párrafo uno.", "Párrafo dos."]},
            {"heading": "Sección dos", "paragraphs": ["Otro párrafo."]},
        ],
        "hero_image": None,
    })
    try:
        response = client.get("/blog/guide-fixture")
        assert response.status_code == 200
        body = response.text
        assert "Sección uno" in body
        assert "Párrafo dos." in body
        assert "Sección dos" in body
    finally:
        BLOG_POSTS.pop()
```

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_blog_guide_sections.py -v`
Expected: FAIL (200 but sections missing — "Sección uno" not in body).

- [ ] **Step 3: Render guide sections**

In `templates/blog_post.html`, insert between the header block (after `</div>` of the header, line ~60) and the organizer aside:

```html
    {% for section in post.get("guide", []) %}
    <section class="glass-panel rounded-2xl p-8 mb-8">
        <h2 class="text-2xl font-bold mb-4">{{ section.heading }}</h2>
        {% for paragraph in section.paragraphs %}
        <p class="text-gray-300 leading-relaxed mb-3">{{ paragraph }}</p>
        {% endfor %}
    </section>
    {% endfor %}
```

- [ ] **Step 4: Run to verify GREEN**

Run: `venv/bin/python -m pytest tests/test_blog_guide_sections.py tests/test_editorial_filtering.py -v`
Expected: PASS; goldens byte-identical (posts without `guide` render nothing new).

- [ ] **Step 5: Commit**

```bash
git add templates/blog_post.html tests/test_blog_guide_sections.py
git commit -m "feat(blog): optional guide sections for text-only posts"
```

---

### Task 11: Informational posts (3, text-only)

**Files:**
- Modify: `blog_config.py` (3 new entries at the top, under `# --- NAVIDAD ---`)
- Modify: `tests/test_christmas_guide.py` (extend the sitemap/renders test list)
- Regenerate: `tests/baselines/editorial_off_sitemap.html`

- [ ] **Step 1: Write the failing tests**

In `tests/test_christmas_guide.py`, extend the existing parametrization (find the slug list used by render/sitemap tests and add):

```python
NEW_GUIDE_SLUGS = [
    "como-organizar-amigo-invisible",
    "reglas-del-amigo-invisible",
    "frases-para-el-amigo-invisible",
]
```

Parametrize the existing "renders a curated product" style test over these slugs asserting: 200, single H1 with the post title, canonical, URL present in `sitemap.xml`, and — for these three — at least two `<h2>` guide headings and an `/amigo-invisible` link (organizer aside).

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_christmas_guide.py -v`
Expected: FAIL (404s — posts don't exist).

- [ ] **Step 3: Add the three posts to `blog_config.py`**

Insert after the christmas entry:

```python
    {
        "slug": "como-organizar-amigo-invisible",
        "title": "Cómo organizar un amigo invisible paso a paso",
        "description": "Los pasos concretos para montar el intercambio: fijar presupuesto y fecha, invitar al grupo, hacer el sorteo y consultar las listas de deseos.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Cómo funciona el amigo invisible", "paragraphs": [
                "El amigo invisible (o amigo secreto) es un intercambio en el que cada participante regala a una sola persona asignada al azar, sin que esta sepa quién le regaló. El sorteo se hace una vez y cada quien prepara su regalo para la fecha acordada.",
                "En Regálame el sorteo impide que alguien se asigne a sí mismo y permite configurar vetos, útiles cuando dos personas no deberían regalarse entre sí.",
            ]},
            {"heading": "Antes del sorteo: presupuesto, fecha y grupo", "paragraphs": [
                "Acordad primero el presupuesto máximo: es la regla que evita situaciones incómodas. Después fijad la fecha del intercambio y dejad margen para que cada quien piense su regalo.",
                "Cread el grupo en Regálame, indicad nombre, fecha y presupuesto, y compartid el enlace de invitación por WhatsApp o email. Cada participante se une con su cuenta.",
            ]},
            {"heading": "El día del intercambio", "paragraphs": [
                "Antes de abrir los regalos, cada participante puede repasar la lista de deseos de su asignado: es la referencia más fiable para acertar. Los resultados del sorteo se consultan dentro de la aplicación, nunca se comparten por chat.",
            ]},
        ],
        "hero_image": None,
    },
    {
        "slug": "reglas-del-amigo-invisible",
        "title": "Reglas del amigo invisible: cómo se juega",
        "description": "Las reglas básicas del amigo invisible, las variantes más habituales y cómo evitar los malentendidos típicos del intercambio.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Las reglas básicas", "paragraphs": [
                "Presupuesto pactado por todos y respeto estricto del secreto: nadie revela a quién le toca regalar hasta el día del intercambio. El sorteo debe ser aleatorio y excluir la autoasignación.",
                "Quien no pueda participar debe decirlo antes del sorteo: después suele implicar repetir todo el proceso.",
            ]},
            {"heading": "Variantes habituales", "paragraphs": [
                "Vetos (parejas o enemistades que no deben tocarse), temáticas (productos hechos a mano, libros, locales) o límites de precio por tramos. En grupos grandes, un intervalo de entrega más ancho evita prisas.",
                "La lista de deseos opcional es la variante más útil: el regalo sigue siendo sorpresa, pero acierta. En Regálame cada participante puede publicar la suya.",
            ]},
        ],
        "hero_image": None,
    },
    {
        "slug": "frases-para-el-amigo-invisible",
        "title": "Frases para el amigo invisible: para el grupo, el papelito y el regalo",
        "description": "Frases cortas para invitar al grupo, para el papel del sorteo y para acompañar el regalo, con tono directo y sin cursilerías.",
        "organizer_aside": True,
        "guide": [
            {"heading": "Para invitar al grupo", "paragraphs": [
                "\"Nos falta la mejor parte del plan: el amigo invisible. Entra en el grupo y elige tu lista de deseos.\" · \"Presupuesto ajustado, sorpresas aseguradas: apúntate al intercambio.\"",
                "\"Si el año pasado te tocó el regalo aburrido, este año toca mejorar: apúntate y pon ideas en tu lista.\"",
            ]},
            {"heading": "Para el papelito o la dedicatoria", "paragraphs": [
                "\"De alguien invisible con mucho gusto.\" · \"Elegido al azar, acertado de verdad.\" · \"El secreto me lo llevo, el regalo te lo llevo a ti.\"",
                "\"Que no se nota quién fue, pero que se nota que acerté.\" · \"Regalo con vuestra lista por delante: no fallé.\"",
            ]},
            {"heading": "Con humor (sin pasarse)", "paragraphs": [
                "\"Tu amigo invisible te conoce mejor de lo que crees... o tuvimos suerte.\" · \"He respetado el presupuesto. El gusto no tenía límite.\"",
                "\"Del anonimato más elegante: ni un pista, ni un fallo.\"",
            ]},
        ],
        "hero_image": None,
    },
```

- [ ] **Step 4: Run to verify GREEN, then regenerate the sitemap golden**

Run: `venv/bin/python -m pytest tests/test_christmas_guide.py tests/test_editorial_filtering.py -v`
Expected: christmas guide tests PASS; editorial golden sitemap test FAILS (3 new URLs) — regenerate with
`venv/bin/python -m pytest tests/test_editorial_filtering.py --editorial-update-baselines`
then diff `tests/baselines/editorial_off_sitemap.html` against git HEAD: the diff must contain ONLY the three new `<url>` blocks. Re-run the suite:
`venv/bin/python -m pytest tests/test_editorial_filtering.py -v` Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add blog_config.py tests/test_christmas_guide.py tests/baselines/editorial_off_sitemap.html
git commit -m "feat(blog): informational amigo-invisible guides (organize, rules, phrases)"
```

---

### Task 12: Multi-category criteria in blog posts

**Files:**
- Modify: `services.py` (`get_blog_post_detail` and `get_blog_posts_with_covers`)
- Modify: `tests/test_catalog.py`

- [ ] **Step 1: Write the failing test**

Append to `tests/test_catalog.py` (mirror the fixture style of `test_get_blog_post_detail_category_criteria` at line 453 — seed products in at least two categories):

```python
def test_get_blog_post_detail_accepts_category_list(session_with_seed):
    BLOG_POSTS.append({
        "slug": "multi-cat-fixture",
        "title": "Multi categoría",
        "description": "prueba",
        "criteria": {"categories": ["Electrónica", "Juguetes y juegos"], "limit": 3},
        "hero_image": None,
    })
    try:
        post, products = get_blog_post_detail(session_with_seed, "multi-cat-fixture")
        assert len(products) <= 3
        cats = {p.category_slug for p in products}
        assert cats <= {"electronica", "juguetes-y-juegos"}
        assert len(cats) >= 1
    finally:
        BLOG_POSTS.pop()
```

(Adapt `session_with_seed` to the exact fixture name used by the neighboring test — read lines 440-470 of `tests/test_catalog.py` and reuse it.)

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_catalog.py -v -k multi_cat`
Expected: FAIL (list resolved as empty — `criteria.get("categories")` is ignored today).

- [ ] **Step 3: Implement the list branch**

In `services.py`, replace the body of `get_blog_post_detail`'s `else:` branch (lines ~287-304) with:

```python
    else:
        categories = criteria.get("categories")
        if isinstance(categories, (list, tuple)) and categories:
            slugs = [slugify(str(name)) for name in categories]
        elif "category" in criteria:
            slugs = [slugify(criteria["category"])]
        else:
            # No category at all (e.g. max_price-only posts like
            # regalos-baratos-menos-20-euros): keep the historical
            # whole-catalog search by passing category_slug=None.
            slugs = [None]

        products = []
        seen_asins = set()
        for category_slug in slugs:
            page = 1
            while True:
                result = search_products(session, CatalogQuery(
                    category_slug=category_slug,
                    max_price=criteria.get("max_price"),
                    page=page,
                    per_page=MAX_PER_PAGE,
                ))
                for item in result.items:
                    if item.asin not in seen_asins:
                        seen_asins.add(item.asin)
                        products.append(item)
                if limit is not None and len(products) >= limit:
                    products = products[:limit]
                    return _hero(post, products)
                if page >= result.total_pages or not result.items:
                    break
                page += 1
```

And extract the existing hero fallback into a module-level helper used by both return paths:

```python
def _hero(post, products):
    if products and not post.get("hero_image"):
        return {**post, "hero_image": products[0].image_url}
    return post
```

(The function's final `return post, products` becomes `return _hero(post, products)`; the `items` branch keeps its behavior identical.)

In `get_blog_posts_with_covers`, extend the slug resolution the same way:

```python
        criteria = post.get("criteria", {})
        categories = criteria.get("categories")
        if isinstance(categories, (list, tuple)) and categories:
            slugs = [slugify(str(name)) for name in categories]
        else:
            slugs = [slugify(criteria["category"])] if "category" in criteria else []
        cover = None
        for category_slug in slugs:
            result = search_products(session, CatalogQuery(
                category_slug=category_slug,
                max_price=criteria.get("max_price"),
                page=1,
                per_page=MAX_PER_PAGE,
            ))
            cover = next(
                (item.image_url for item in result.items
                 if item.image_url and item.image_url not in used_images),
                None,
            ) or (result.items[0].image_url if result.items else None)
            if cover:
                break
```

(Keep the `used_images` bookkeeping exactly as it is.)

- [ ] **Step 4: Run to verify GREEN and no regressions**

Run: `venv/bin/python -m pytest tests/test_catalog.py tests/test_editorial_filtering.py tests/test_christmas_guide.py -v`
Expected: PASS everywhere (single-category posts unchanged; covers for multi-category posts resolve from the first category with visible products).

- [ ] **Step 5: Commit**

```bash
git add services.py tests/test_catalog.py
git commit -m "feat(blog): multi-category criteria with shared limit"
```

---

### Task 13: Audience posts (2, curated lists) + human review checkpoint

**Files:**
- Modify: `blog_config.py` (2 new entries)
- Modify: `tests/test_christmas_guide.py` (extend parametrization)
- Regenerate: `tests/baselines/editorial_off_sitemap.html`

- [ ] **Step 1: Write the failing tests**

Extend the Task 11 parametrization with:

```python
NEW_AUDIENCE_SLUGS = [
    "amigo-invisible-para-companeros-de-trabajo",
    "amigo-invisible-para-ninos",
]
```

Same assertions as Task 11 (200, single H1, canonical, in sitemap) but WITHOUT the guide/aside assertions: audience posts are product lists.

- [ ] **Step 2: Run to verify RED**

Run: `venv/bin/python -m pytest tests/test_christmas_guide.py -v`
Expected: FAIL (404s).

- [ ] **Step 3: Add the two posts to `blog_config.py`**

```python
    {
        "slug": "amigo-invisible-para-companeros-de-trabajo",
        "title": "Amigo invisible para compañeros de trabajo: ideas que aciertan",
        "description": "Regalos seguros para la oficina: útiles, neutros y dentro del presupuesto típico del intercambio de empresa.",
        "criteria": {
            "categories": ["Electrónica", "Hogar y cocina", "Libros", "Belleza"],
            "max_price": 15.0,
            "limit": 20,
        },
        "hero_image": None,
    },
    {
        "slug": "amigo-invisible-para-ninos",
        "title": "Amigo invisible para niños: regalos que aciertan",
        "description": "Selección de juguetes y libros para intercambios infantiles, con opciones para varios rangos de edad.",
        "criteria": {
            "categories": ["Juguetes y juegos", "Libros"],
            "limit": 20,
        },
        "hero_image": None,
    },
```

- [ ] **Step 4: Run to verify GREEN, regenerate sitemap golden**

Same sequence as Task 11 Step 4: focused suite, regenerate baselines, verify the sitemap diff contains ONLY the two new `<url>` blocks, full re-run PASS.

- [ ] **Step 5: HUMAN REVIEW CHECKPOINT — show the rendered lists to the user**

Render both pages locally (`uvicorn main:app` and open `/blog/amigo-invisible-para-companeros-de-trabajo` and `/blog/amigo-invisible-para-ninos`), list the products shown, and ask the user to approve or request swaps. The Step 6 commit happens AFTER this approval; if the user requests swaps, adjust `criteria` before committing.

- [ ] **Step 6: Commit**

```bash
git add blog_config.py tests/test_christmas_guide.py tests/baselines/editorial_off_sitemap.html
git commit -m "feat(blog): audience posts for coworkers and kids (amigo invisible)"
```

---

### Task 14: Home -> christmas post link (verify, add if missing)

**Files:**
- Possibly modify: `templates/index.html` (only if the link is missing)
- Modify: `tests/test_seo_landings.py`

- [ ] **Step 1: Write the characterization test**

Append to `tests/test_seo_landings.py`:

```python
def test_home_links_the_christmas_guide(client):
    soup = page(client, "/")
    assert soup.main.find("a", href="/blog/regalos-navidad-mas-deseados")
```

- [ ] **Step 2: Run it**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py -v -k christmas`
Expected: either PASS already (link exists — record observed in the ODD doc and stop here) or FAIL.

- [ ] **Step 3: If RED: add the link**

In `templates/index.html`, find the "Listas para Navidad y amigo invisible" section (see `tests/baselines/editorial_off_home.html:268`) and add alongside the organizer link:

```html
<a href="/blog/regalos-navidad-mas-deseados" class="text-pink-300 hover:text-white underline">Los regalos más deseados para Navidad</a>
```

- [ ] **Step 4: If code changed: run and commit**

Run: `venv/bin/python -m pytest tests/test_seo_landings.py tests/test_editorial_filtering.py -v`
Expected: PASS; if the home golden changed, regenerate and verify the diff is exactly the new anchor.

```bash
git add templates/index.html tests/test_seo_landings.py tests/baselines/
git commit -m "feat(seo): link the christmas guide from home"
```

---

### Task 15: Full verification, ODD doc close-out, delivery ask

**Files:**
- Modify: `odd/tasks/amigo-invisible-seo-campaign.md`

- [ ] **Step 1: Full suite**

Run: `venv/bin/python -m pytest`
Expected: all PASS.

- [ ] **Step 2: Update the ODD doc**

Record per-task verification evidence (RED/GREEN counts, commit hashes) in `odd/tasks/amigo-invisible-seo-campaign.md` (Review workload table + TDD observed results + Progress).

- [ ] **Step 3: Delivery strategy ask (ask-on-risk)**

The forecast exceeds ~400 authored lines. Ask the user ONCE: `stacked-to-main` chain, `feature-branch-chain`, or `single-pr`. Record the choice in the ODD doc. Do not push or open PRs without the user's explicit go-ahead.

- [ ] **Step 4: Record the December measurement reminder**

In the ODD doc Progress section, note: re-run `venv/bin/python tools/gsc_report.py --days 90 --out tools/reports/gsc-december.md` during the first week of December 2026 and compare against `tools/reports/gsc-baseline-*.md` (Task 9 = T9 in the ODD doc).
