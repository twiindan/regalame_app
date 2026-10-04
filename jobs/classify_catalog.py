"""Classify active catalog products into editorial states via the provider.

Mirrors ``jobs/refresh_catalog.py``: a synchronous ``run(session, ...)`` seam
with an injectable ``classify_fn`` (tests inject a fake, so CI makes zero network
calls) plus a ``main()`` CLI. A decision row is written only from a validated
classification result, so provider failures are never cached.
"""

import argparse
import os
import sys
import time

from sqlmodel import Session

import curation
import curation_provider
from curation import EDITORIAL_POLICY_VERSION
from curation_provider import EDITORIAL_PROVIDER_MODEL
from database import engine

#: Decisions are committed every this many products; the decision table itself is
#: the resumability checkpoint, so a restarted run skips committed work.
EDITORIAL_JOB_COMMIT_EVERY = int(os.getenv("EDITORIAL_JOB_COMMIT_EVERY", "25"))


def _now() -> float:
    """Monotonic clock seam (monkeypatched by the bounds tests)."""
    return time.monotonic()


def _product_item(product) -> dict:
    """The minimal provider item: title, observed category, and category slug.

    The v1 context rule needs the product's own ``category_slug`` so a
    ``contextual`` decision can be validated against a live ``/ideas/{slug}``.
    No user or wish data ever enters this payload.
    """
    return {
        "title": product.title,
        "category": product.category,
        "category_slug": product.category_slug,
    }


def run(session, classify_fn=curation_provider.classify_product, *, dry_run=False,
        limit=None, max_seconds=None, log=print) -> int:
    """Classify the pending/stale active products. Returns the exit code.

    ``classify_fn`` is a callable ``item -> ClassificationResult | None``;
    ``None`` means the provider call failed or returned an invalid response, in
    which case no decision row is written (failure-not-cached). The decision
    table is the only progress state, so a restarted run skips committed work.
    """
    started = _now()
    pending = curation.pending_products(
        session, policy_version=EDITORIAL_POLICY_VERSION, model_id=EDITORIAL_PROVIDER_MODEL
    )

    if dry_run:
        log(f"dry-run pending={len(pending)} elapsed={_now() - started:.1f}")
        return 0

    commit_every = max(1, EDITORIAL_JOB_COMMIT_EVERY)
    classified = 0
    processed = 0
    batch = 0
    last_committed = 0
    stopped = None

    for product in pending:
        if limit is not None and processed >= limit:
            stopped = "limit"
            break

        result = classify_fn(_product_item(product))
        processed += 1
        if result is not None:
            curation.apply_decision(
                session, product, result,
                model_id=EDITORIAL_PROVIDER_MODEL, policy_version=EDITORIAL_POLICY_VERSION,
            )
            classified += 1

        if processed % commit_every == 0:
            session.commit()
            batch += 1
            last_committed = processed
            _log_progress(log, batch, classified, len(pending), processed, started)

    if processed > last_committed:
        session.commit()
        batch += 1
        _log_progress(log, batch, classified, len(pending), processed, started)

    if stopped is not None:
        log(f"stopped={stopped} processed={processed} classified={classified} "
            f"pending={len(pending) - processed} elapsed={_now() - started:.1f}")
    return 0


def _log_progress(log, batch, classified, total_pending, processed, started) -> None:
    log(f"batch={batch} classified={classified} pending={total_pending - processed} "
        f"elapsed={_now() - started:.1f}")


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Classify catalog products for editorial curation")
    parser.add_argument("--dry-run", action="store_true",
                        help="Select and report without calling the provider or writing")
    parser.add_argument("--limit", type=int, default=None,
                        help="Maximum products to classify this run")
    parser.add_argument("--max-seconds", type=int, default=None,
                        help="Wall-clock bound for this run, in seconds")
    return parser.parse_args(argv)


def main(argv=None, session=None):
    """CLI entry point. Returns the exit code."""
    args = _parse_args(argv)
    if session is not None:
        return run(session, dry_run=args.dry_run, limit=args.limit, max_seconds=args.max_seconds)
    with Session(engine) as owned:
        return run(owned, dry_run=args.dry_run, limit=args.limit, max_seconds=args.max_seconds)


if __name__ == "__main__":
    sys.exit(main())
