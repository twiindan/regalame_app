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
