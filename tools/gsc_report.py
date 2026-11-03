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
