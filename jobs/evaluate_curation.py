"""Offline evaluation gate: stratified sampling, metric math, gate-state upsert.

Reads persisted ``editorial_decision`` rows plus a human-labels JSON file and
records the verdict in the single ``editorial_gate_state`` row. The gate makes
**zero** provider calls: classification quality is measured against human labels,
never by re-asking the model. Mirrors ``jobs/refresh_catalog.py``: a synchronous
``run(session, ...)`` seam plus a ``main()`` CLI.
"""

import json
from dataclasses import dataclass

from sqlmodel import select

import curation
import curation_provider
from curation import EDITORIAL_POLICY_VERSION, EDITORIAL_STATES
from curation_provider import EDITORIAL_PROVIDER_MODEL
from models import EditorialDecision, Product

#: Adopted gate thresholds (concrete so they are testable; re-tunable by
#: updating the specification).
GATE_MIN_OVERALL_AGREEMENT = 0.90      # MUST
GATE_MAX_EXCLUDED_LEAK_RATIO = 0.05    # MUST
GATE_REQUIRED_COVERAGE_RATIO = 1.0     # MUST
GATE_MAX_UNKNOWN_RATIO = 0.10          # SHOULD (pass but flag)


class LabelsError(ValueError):
    """The human-labels file is malformed or partially filled."""


@dataclass(frozen=True)
class GateReport:
    """The measured gate metrics and verdict (before persistence)."""

    gate_passed: bool
    coverage_ratio: float
    unknown_ratio: float
    overall_agreement: float
    excluded_leak_ratio: float
    policy_version: str
    model_id: str
    unknown_flagged: bool
    labeled_count: int


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


def _decisions_by_product(session):
    return {
        decision.product_id: decision
        for decision in session.exec(select(EditorialDecision)).all()
    }


def evaluate(session, labels_path):
    """Measure classification quality against human labels. No gate write."""
    labels = _load_labels(labels_path)
    policy_version = EDITORIAL_POLICY_VERSION
    model_id = EDITORIAL_PROVIDER_MODEL
    decisions = _decisions_by_product(session)
    by_asin = {product.asin: product for product in session.exec(select(Product)).all()}

    matches = 0
    excluded_labeled = 0
    leaked = 0
    for asin, expected in labels.items():
        product = by_asin.get(asin)
        ai_state = curation.effective_state(
            decisions.get(product.id) if product is not None else None
        )
        if ai_state == expected:
            matches += 1
        if expected == "excluded":
            excluded_labeled += 1
            if ai_state == "eligible":
                leaked += 1

    overall_agreement = matches / len(labels)
    excluded_leak_ratio = leaked / excluded_labeled if excluded_labeled else 0.0

    active = session.exec(
        select(Product).where(Product.is_active == True)  # noqa: E712
    ).all()
    if active:
        # Coverage reuses the job's own pending definition, so backfill
        # completeness cannot drift from the classification job.
        pending = curation.pending_products(
            session, policy_version=policy_version, model_id=model_id
        )
        coverage_ratio = (len(active) - len(pending)) / len(active)
        unknown_count = sum(
            1 for product in active
            if curation.effective_state(decisions.get(product.id)) == "unknown"
        )
        unknown_ratio = unknown_count / len(active)
    else:
        coverage_ratio = 1.0
        unknown_ratio = 0.0

    gate_passed = (
        overall_agreement >= GATE_MIN_OVERALL_AGREEMENT
        and excluded_leak_ratio <= GATE_MAX_EXCLUDED_LEAK_RATIO
        and coverage_ratio == GATE_REQUIRED_COVERAGE_RATIO
    )
    return GateReport(
        gate_passed=gate_passed,
        coverage_ratio=coverage_ratio,
        unknown_ratio=unknown_ratio,
        overall_agreement=overall_agreement,
        excluded_leak_ratio=excluded_leak_ratio,
        policy_version=policy_version,
        model_id=model_id,
        unknown_flagged=unknown_ratio > GATE_MAX_UNKNOWN_RATIO,
        labeled_count=len(labels),
    )
