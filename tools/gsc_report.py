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
    Retries 429/5xx with 1/2/4s backoff (3 retry attempts), then raises.
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
        # Initial call + 3 retries with 1/2/4s backoff; a 4th consecutive
        # failure falls through to raise_for_status.
        for attempt in range(4):
            response = session.post(url, json=payload)
            if response.status_code not in (429, 500, 502, 503):
                break
            if attempt < 3:
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
