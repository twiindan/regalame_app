"""Classify active catalog products into editorial states via the provider.

Mirrors ``jobs/refresh_catalog.py``: a synchronous ``run(session, ...)`` seam
with an injectable ``classify_fn`` (tests inject a fake, so CI makes zero network
calls) plus a ``main()`` CLI. A decision row is written only from a validated
classification result, so provider failures are never cached.
"""

import argparse
import os
import sys
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait

from sqlmodel import Session

import curation
import curation_provider
from curation import EDITORIAL_POLICY_VERSION
from curation_provider import EDITORIAL_PROVIDER_MODEL
from database import engine

#: Decisions are committed every this many products; the decision table itself is
#: the resumability checkpoint, so a restarted run skips committed work.
EDITORIAL_JOB_COMMIT_EVERY = int(os.getenv("EDITORIAL_JOB_COMMIT_EVERY", "25"))

#: Sequential run bounds. Reaching any bound stops cleanly (exit 0) with the
#: remaining products deferred to a future run.
EDITORIAL_JOB_RPM = int(os.getenv("EDITORIAL_JOB_RPM", "60"))
EDITORIAL_JOB_MAX_SECONDS = int(os.getenv("EDITORIAL_JOB_MAX_SECONDS", "3300"))
EDITORIAL_JOB_MAX_PRODUCTS = int(os.getenv("EDITORIAL_JOB_MAX_PRODUCTS", "500"))

#: Provider calls allowed in flight at once. ``1`` (the default) preserves the
#: original sequential behavior. Above ``1`` the transport runs on worker threads
#: while every DB read/write/commit stays on the main thread (SQLModel ``Session``
#: is not thread-safe). Leaving one of NaN's five concurrent slots free, the
#: production value is ``4``.
EDITORIAL_JOB_CONCURRENCY = int(os.getenv("EDITORIAL_JOB_CONCURRENCY", "1"))


def _now() -> float:
    """Monotonic clock seam (monkeypatched by the bounds tests)."""
    return time.monotonic()


def _sleep(seconds: float) -> None:
    """Sleep seam (monkeypatched by the bounds tests)."""
    time.sleep(seconds)


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

    Runs sequentially when ``EDITORIAL_JOB_CONCURRENCY <= 1`` (the historical
    behavior) and through a bounded thread pool otherwise. In both cases every DB
    read/write/commit happens on the main thread.
    """
    started = _now()
    pending = curation.pending_products(
        session, policy_version=EDITORIAL_POLICY_VERSION, model_id=EDITORIAL_PROVIDER_MODEL
    )

    if dry_run:
        log(f"dry-run pending={len(pending)} elapsed={_now() - started:.1f}")
        return 0

    if limit is not None:
        product_cap, cap_reason = limit, "limit"
    else:
        product_cap, cap_reason = EDITORIAL_JOB_MAX_PRODUCTS, "max_products"
    max_seconds = max_seconds if max_seconds is not None else EDITORIAL_JOB_MAX_SECONDS
    commit_every = max(1, EDITORIAL_JOB_COMMIT_EVERY)
    concurrency = max(1, EDITORIAL_JOB_CONCURRENCY)

    log(f"classify: start pending={len(pending)} concurrency={concurrency} "
        f"rpm={EDITORIAL_JOB_RPM} commit_every={commit_every} "
        f"max_products={product_cap} max_seconds={max_seconds} "
        f"model={EDITORIAL_PROVIDER_MODEL} policy={EDITORIAL_POLICY_VERSION}")

    if concurrency > 1:
        return _run_concurrent(
            session, classify_fn, pending, concurrency=concurrency,
            product_cap=product_cap, cap_reason=cap_reason, max_seconds=max_seconds,
            commit_every=commit_every, started=started, log=log,
        )
    return _run_sequential(
        session, classify_fn, pending, product_cap=product_cap, cap_reason=cap_reason,
        max_seconds=max_seconds, commit_every=commit_every, started=started, log=log,
    )


class _RateLimiter:
    """Thread-safe start-time pacer enforcing ``min_interval`` between requests.

    A shared lock plus a single last-start timestamp keeps the aggregate start
    rate at or below the configured RPM even while several calls are in flight.
    """

    def __init__(self, min_interval, now, sleep):
        self.min_interval = min_interval
        self._now = now
        self._sleep = sleep
        self._last = None
        self._lock = threading.Lock()

    def acquire(self):
        if self.min_interval <= 0:
            return
        with self._lock:
            if self._last is not None:
                wait = self.min_interval - (self._now() - self._last)
                if wait > 0:
                    self._sleep(wait)
            self._last = self._now()


def _run_sequential(session, classify_fn, pending, *, product_cap, cap_reason,
                    max_seconds, commit_every, started, log) -> int:
    """The original single-threaded loop, unchanged in behavior."""
    min_interval = 60.0 / EDITORIAL_JOB_RPM if EDITORIAL_JOB_RPM > 0 else 0.0
    classified = 0
    processed = 0
    batch = 0
    last_committed = 0
    last_start = None
    stopped = None

    for product in pending:
        if product_cap is not None and processed >= product_cap:
            stopped = cap_reason
            break

        # Sequential (concurrency 1): space requests out to respect the RPM bound.
        if last_start is not None and min_interval > 0:
            wait = min_interval - (_now() - last_start)
            if wait > 0:
                _sleep(wait)

        if _now() - started >= max_seconds:
            stopped = "max_seconds"
            break

        last_start = _now()
        result = classify_fn(_product_item(product))
        processed += 1
        if result is not None:
            curation.apply_decision(
                session, product, result,
                model_id=EDITORIAL_PROVIDER_MODEL, policy_version=EDITORIAL_POLICY_VERSION,
            )
            classified += 1
            _log_product(log, processed, len(pending), product, result, started)
        else:
            _log_failure(log, processed, len(pending), product, started)

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
    _log_summary(log, processed, classified, len(pending), started)
    return 0


def _run_concurrent(session, classify_fn, pending, *, concurrency, product_cap, cap_reason,
                    max_seconds, commit_every, started, log) -> int:
    """Bounded-concurrency loop: provider calls on workers, all DB on this thread.

    At most ``concurrency`` calls are in flight. Results are collected as futures
    complete and applied to the session on the main thread, then committed in
    batches exactly like the sequential path. The shared ``_RateLimiter`` spaces
    *starts* (not completions) so overlapping calls still respect the RPM bound.
    """
    min_interval = 60.0 / EDITORIAL_JOB_RPM if EDITORIAL_JOB_RPM > 0 else 0.0
    limiter = _RateLimiter(min_interval, _now, _sleep)
    total = len(pending)
    classified = 0
    processed = 0
    batch = 0
    last_committed = 0
    scheduled = 0
    stopped = None
    index = 0
    in_flight = {}

    def collect(product, result, error=None):
        nonlocal classified, processed, batch, last_committed
        processed += 1
        if result is not None:
            curation.apply_decision(
                session, product, result,
                model_id=EDITORIAL_PROVIDER_MODEL, policy_version=EDITORIAL_POLICY_VERSION,
            )
            classified += 1
            _log_product(log, processed, total, product, result, started)
        else:
            _log_failure(log, processed, total, product, started, error)
        if processed % commit_every == 0:
            session.commit()
            batch += 1
            last_committed = processed
            _log_progress(log, batch, classified, total, processed, started)

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        while index < total or in_flight:
            while stopped is None and index < total and len(in_flight) < concurrency:
                if product_cap is not None and scheduled >= product_cap:
                    stopped = cap_reason
                    break
                limiter.acquire()
                if _now() - started >= max_seconds:
                    stopped = "max_seconds"
                    break
                product = pending[index]
                index += 1
                scheduled += 1
                in_flight[executor.submit(classify_fn, _product_item(product))] = product

            if not in_flight:
                break

            done, _ = wait(set(in_flight), return_when=FIRST_COMPLETED)
            for future in done:
                product = in_flight.pop(future)
                error = None
                try:
                    result = future.result()
                except Exception as exc:
                    result = None
                    error = exc
                collect(product, result, error)

    if processed > last_committed:
        session.commit()
        batch += 1
        _log_progress(log, batch, classified, total, processed, started)

    if stopped is not None:
        log(f"stopped={stopped} processed={processed} classified={classified} "
            f"pending={total - processed} elapsed={_now() - started:.1f}")
    _log_summary(log, processed, classified, total, started)
    return 0


def _short(text, limit=80) -> str:
    """A bounded, log-safe rendering of a product field."""
    rendered = "" if text is None else str(text)
    if len(rendered) > limit:
        rendered = rendered[: limit - 3] + "..."
    return rendered


def _log_product(log, index, total, product, result, started) -> None:
    """One activity line per classified product, so a run is observable live."""
    context = result.context if result.context else "-"
    log(f"product={index}/{total} title={_short(product.title)!r} state={result.state} "
        f"context={context} reason={_short(result.reason)!r} elapsed={_now() - started:.1f}")


def _log_failure(log, index, total, product, started, error=None) -> None:
    """One line per failed product; it stays pending for a future run."""
    suffix = f" error={error!r}" if error is not None else ""
    log(f"product={index}/{total} title={_short(product.title)!r} result=failed"
        f"{suffix} elapsed={_now() - started:.1f}")


def _log_summary(log, processed, classified, total, started) -> None:
    """Always emitted, so an operator sees totals even without a batch boundary."""
    log(f"classify: done processed={processed} classified={classified} "
        f"failed={processed - classified} pending={max(0, total - processed)} "
        f"elapsed={_now() - started:.1f}")


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
