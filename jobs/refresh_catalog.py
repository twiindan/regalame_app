"""Daily catalog refresh: scrape the Amazon lists and import them into the DB."""

import json
import os
import tempfile

from sqlmodel import func, select

from catalog import import_from_json
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


def run(session, scrape_fn=scrape_all, dry_run=False, data_dir=None, log=print):
    """Refresh the catalog. Returns the exit code (0 ok, 1 nothing imported)."""
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
        log(f"section={list_key} status=suspicious excluded")

    if not healthy:
        log("refresh: no healthy sections, nothing imported")
        return 1

    stats = import_from_json(session, data_files=healthy, dry_run=dry_run)
    log(f"import: created={stats['created']} updated={stats['updated']} "
        f"lists={stats['lists']} sections_ok={len(healthy)}")
    return 0
