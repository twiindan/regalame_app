"""Daily catalog refresh: scrape the Amazon lists and import them into the DB."""

import argparse
import asyncio
import json
import os
import sys
import tempfile

from sqlmodel import Session, func, select

from catalog import deactivate_absent_products, import_from_json
from database import engine
from models import ProductList
from scraper import SECTIONS, scrape_all

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
    except (OSError, ValueError):
        # ValueError covers both json.JSONDecodeError and UnicodeDecodeError: a file
        # that is not valid UTF-8 must be excluded as suspicious, not abort the run.
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
        # The guard measures raw JSON entries, not importable products: the baseline counts
        # distinct ProductList rows, while import_from_json collapses duplicate ASINs and
        # skips entries without a url. A file padded with duplicates can therefore pass the
        # guard and still import fewer products; the guard targets truncation, not dedup.
        if count == 0 or (previous and count < previous * MIN_HEALTHY_RATIO):
            suspicious.append(list_key)
        else:
            healthy[list_key] = path
    return healthy, sorted(suspicious)


def _scrape_into(out_dir):
    """Bridge the async scraper to the synchronous ``run`` seam.

    ``scraper.scrape_all`` is a coroutine function (it awaits Playwright), while
    ``run`` is synchronous and every injected fake is a plain callable. Without
    this bridge the production path hands a coroutine object to ``classify``.
    """
    return asyncio.run(scrape_all(out_dir))


def run(session, scrape_fn=_scrape_into, dry_run=False, data_dir=None, log=print):
    """Refresh the catalog. Returns the exit code (0 ok, 1 nothing imported).

    ``scrape_fn`` is a **synchronous** callable returning the ``{list_key: path}``
    map; the production default ``_scrape_into`` wraps the async scraper. It must
    not be called from within a running event loop, since the default bridge uses
    ``asyncio.run``.
    """
    baseline = baseline_counts(session)
    if data_dir:
        produced = {
            section.list_key: os.path.join(data_dir, section.filename)
            for section in SECTIONS
            if os.path.exists(os.path.join(data_dir, section.filename))
        }
        return _finish(session, produced, baseline, dry_run, log)
    with tempfile.TemporaryDirectory(prefix="catalog_run_") as out_dir:
        produced = scrape_fn(out_dir)
        return _finish(session, produced, baseline, dry_run, log)


def _finish(session, produced, baseline, dry_run, log):
    healthy, suspicious = classify(produced, baseline)
    for list_key in suspicious:
        log(f"section={list_key} status=suspicious excluded "
            f"produced={_count_items(produced[list_key])} baseline={baseline.get(list_key, 0)}")
    for section in SECTIONS:
        if section.list_key not in produced:
            log(f"section={section.list_key} status=absent not-produced")

    # Keep this early return: handing an empty data_files to import_from_json would
    # fall back to its DATA_FILES default and re-import the repository's root JSONs.
    if not healthy:
        log("refresh: no healthy sections, nothing imported")
        return 1

    stats = import_from_json(session, data_files=healthy, dry_run=dry_run)
    log(f"import: created={stats['created']} updated={stats['updated']} "
        f"lists={stats['lists']} sections_ok={len(healthy)}")

    # Deactivation runs only on a fully healthy run: on a partial run a product
    # could be absent merely because its section failed.
    if not dry_run and not suspicious and len(healthy) == len(SECTIONS):
        log(f"deactivated={deactivate_absent_products(session, list_keys=sorted(healthy))}")
    return 0


def _parse_args(argv):
    parser = argparse.ArgumentParser(description="Refresh the Amazon catalog")
    parser.add_argument("--dry-run", action="store_true",
                        help="Report the changes without writing them")
    parser.add_argument("--data-dir", default=None,
                        help="Import the JSON files already in DIR instead of scraping")
    return parser.parse_args(argv)


def main(argv=None, session=None):
    """CLI entry point. Returns the exit code."""
    args = _parse_args(argv)
    if session is not None:
        return run(session, dry_run=args.dry_run, data_dir=args.data_dir)
    with Session(engine) as owned:
        return run(owned, dry_run=args.dry_run, data_dir=args.data_dir)


if __name__ == "__main__":
    sys.exit(main())
