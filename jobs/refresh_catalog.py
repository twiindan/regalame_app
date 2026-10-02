"""Daily catalog refresh: scrape the Amazon lists and import them into the DB."""

import json

from sqlmodel import func, select

from models import ProductList

# A section below this fraction of its previous count is treated as truncated.
MIN_HEALTHY_RATIO = 0.5


def baseline_counts(session):
    """Current number of products per list, read before the import."""
    rows = session.exec(
        select(ProductList.list_key, func.count()).group_by(ProductList.list_key)
    ).all()
    return {list_key: count for list_key, count in rows}


def _count_items(path):
    """Number of products in a produced file; 0 when missing or unreadable."""
    try:
        with open(path, encoding="utf-8") as handle:
            items = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return 0
    return len(items) if isinstance(items, list) else 0


def classify(produced, baseline):
    """Split produced files into (healthy, suspicious) list keys.

    A section is suspicious when it is unreadable, empty, or shorter than
    ``MIN_HEALTHY_RATIO`` of what that list had before. Suspicious sections are
    never imported, so their ranks and their products stay untouched. A list with
    no baseline (first run) has no reference to fall short of.
    """
    healthy, suspicious = {}, []
    for list_key, path in produced.items():
        count = _count_items(path)
        previous = baseline.get(list_key, 0)
        if count == 0 or (previous and count < previous * MIN_HEALTHY_RATIO):
            suspicious.append(list_key)
        else:
            healthy[list_key] = path
    return healthy, sorted(suspicious)
