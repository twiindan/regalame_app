"""Editorial curation policy and query-side logic.

Pure functions plus SQL predicate builders: input fingerprints, pending-product
selection, decision persistence, and the effective-state resolution. This module
performs no I/O of its own.
"""

import hashlib
import json
import os
from typing import Optional, Protocol, runtime_checkable

from sqlalchemy import func
from sqlmodel import Session, select

from models import EditorialDecision, Product, utcnow_naive

# --------------------------------------------------------------------------- #
# Policy constants
# --------------------------------------------------------------------------- #

#: The four editorial states. A product with no decision is treated as ``unknown``.
EDITORIAL_STATES = ("eligible", "contextual", "excluded", "unknown")

#: Policy/schema version in effect. Bumping it invalidates every AI fingerprint.
EDITORIAL_POLICY_VERSION = "1"

#: Configured filter mode. Read once at import; ``off`` is the shadow default.
EDITORIAL_FILTER_MODE = os.getenv("EDITORIAL_FILTER_MODE", "off")

#: Closed contextual vocabulary. Empty at v1: a contextual decision is valid only
#: when its context equals the product's own ``category_slug`` (so every
#: contextual product has a live ``/ideas/{slug}`` surface). Widening this to a
#: curated superset is a ``EDITORIAL_POLICY_VERSION`` bump.
EDITORIAL_CONTEXTS: frozenset[str] = frozenset()


@runtime_checkable
class DecisionResult(Protocol):
    """Structural contract for a provider classification result.

    ``curation_provider.ClassificationResult`` satisfies this protocol; only the
    three read fields are required here.
    """

    state: str
    context: Optional[str]
    reason: str


# --------------------------------------------------------------------------- #
# Input fingerprint
# --------------------------------------------------------------------------- #


def compute_fingerprint(title_normalized: str, category: str, policy_version: str,
                        model_id: str) -> str:
    """SHA-256 of the JSON-canonical input tuple that governs reclassification.

    Inputs are exactly the normalized title, the last observed single category,
    the policy version, and the model identifier. Price, rank, ``scraped_at``,
    ``updated_at`` and ``is_active`` are deliberately not inputs.
    """
    payload = json.dumps(
        [title_normalized, category, policy_version, model_id], ensure_ascii=False
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _effective_state_column():
    """SQL expression for the effective state: a manual override always wins."""
    return func.coalesce(EditorialDecision.manual_state, EditorialDecision.state)


def _effective_context_column():
    """SQL expression for the effective context: a manual override always wins."""
    return func.coalesce(EditorialDecision.manual_context, EditorialDecision.context)


def effective_state(decision: Optional[EditorialDecision]) -> str:
    """Effective state of a decision row; a missing/all-NULL row is ``unknown``.

    ``unknown`` is never promoted to a visible state by absence or defaulting.
    """
    if decision is None:
        return "unknown"
    return decision.manual_state or decision.state or "unknown"


# --------------------------------------------------------------------------- #
# Selection + persistence
# --------------------------------------------------------------------------- #


def _expected_fingerprint(product: Product, policy_version: str, model_id: str) -> str:
    return compute_fingerprint(
        product.title_normalized, product.category, policy_version, model_id
    )


def pending_products(session: Session, *, policy_version: str, model_id: str,
                     limit: Optional[int] = None) -> list[Product]:
    """Active products needing classification: no row, or a fingerprint mismatch.

    Products with a manual override are never returned — the job must not spend
    provider calls whose result the override would discard.
    """
    products = session.exec(
        select(Product).where(Product.is_active == True).order_by(Product.id)  # noqa: E712
    ).all()
    decisions = {
        decision.product_id: decision
        for decision in session.exec(select(EditorialDecision)).all()
    }

    pending: list[Product] = []
    for product in products:
        decision = decisions.get(product.id)
        if decision is not None and decision.manual_state is not None:
            continue
        expected = _expected_fingerprint(product, policy_version, model_id)
        if decision is None or decision.input_fingerprint != expected:
            pending.append(product)
            if limit is not None and len(pending) >= limit:
                break
    return pending


def apply_decision(session: Session, product: Product, result: DecisionResult, *,
                   model_id: str, policy_version: str) -> EditorialDecision:
    """Upsert the AI-produced decision for ``product`` (writes AI columns only).

    A manual override on the row is left untouched; callers committing in batches
    own the transaction.
    """
    decision = session.exec(
        select(EditorialDecision).where(EditorialDecision.product_id == product.id)
    ).first()
    if decision is None:
        decision = EditorialDecision(product_id=product.id)

    decision.state = result.state
    decision.context = result.context if result.state == "contextual" else None
    decision.reason = result.reason
    decision.model_id = model_id
    decision.policy_version = policy_version
    decision.input_fingerprint = _expected_fingerprint(product, policy_version, model_id)
    decision.classified_at = utcnow_naive()

    session.add(decision)
    session.flush()
    return decision
