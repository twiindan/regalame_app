"""Daily catalog refresh: scrape the Amazon lists and import them into the DB."""

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
