"""Offline evaluation gate: stratified sampling, metric math, gate-state upsert.

Reads persisted ``editorial_decision`` rows plus a human-labels JSON file and
records the verdict in the single ``editorial_gate_state`` row. The gate makes
**zero** provider calls: classification quality is measured against human labels,
never by re-asking the model. Mirrors ``jobs/refresh_catalog.py``: a synchronous
``run(session, ...)`` seam plus a ``main()`` CLI.
"""

import json

from sqlmodel import select

from curation import EDITORIAL_STATES
from models import Product


class LabelsError(ValueError):
    """The human-labels file is malformed or partially filled."""


def sample_products(session, *, total=100):
    """A deterministic, category-stratified sample of active products.

    Products are grouped by ``category_slug`` (iterated in sorted order) and
    drawn round-robin so the sample spreads across catalog categories rather than
    front-loading one stratum. Within a stratum the order is by primary key.
    """
    products = session.exec(
        select(Product)
        .where(Product.is_active == True)  # noqa: E712
        .order_by(Product.category_slug, Product.id)
    ).all()
    strata: dict[str, list[Product]] = {}
    for product in products:
        strata.setdefault(product.category_slug, []).append(product)

    sample: list[Product] = []
    depth = 0
    while len(sample) < total:
        added = False
        for slug in sorted(strata):
            stratum = strata[slug]
            if depth < len(stratum):
                sample.append(stratum[depth])
                added = True
                if len(sample) >= total:
                    break
        if not added:
            break
        depth += 1
    return sample


def _load_labels(labels_path):
    """Parse and validate the human-labels file. Raises ``LabelsError``.

    Every entry must carry a non-empty ``asin`` and an ``expected_state`` in the
    editorial-state enum; a blank entry means a partially-filled file, rejected
    before any gate row is written.
    """
    try:
        with open(labels_path, encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        raise LabelsError(f"unreadable labels file: {exc}") from exc

    if not isinstance(payload, dict):
        raise LabelsError("labels file must be a JSON object")
    entries = payload.get("labels")
    if not isinstance(entries, list) or not entries:
        raise LabelsError("labels file must contain a non-empty 'labels' list")

    labels: dict[str, str] = {}
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise LabelsError(f"label #{index} must be an object")
        asin = entry.get("asin")
        expected = entry.get("expected_state")
        if not isinstance(asin, str) or not asin:
            raise LabelsError(f"label #{index} is missing an asin")
        if expected not in EDITORIAL_STATES:
            raise LabelsError(f"label #{index} has an invalid expected_state")
        labels[asin] = expected
    return labels
