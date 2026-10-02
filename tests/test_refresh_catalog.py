"""Catalog refresh orchestration: health classification and failure containment."""

import json
import os

from sqlmodel import func, select

import jobs.refresh_catalog as refresh_catalog
from models import Product, ProductList
from scraper import SECTIONS

FILENAMES = {section.list_key: section.filename for section in SECTIONS}
FULL = {"bestsellers": 12, "trends": 12, "desired": 12}


def product_json(list_key, index, title=None):
    asin = f"B{list_key[:2].upper()}{index:07d}"
    return {"category": "Electrónica", "title": title or f"Producto {list_key} {index}",
            "image": f"https://img/{asin}.jpg",
            "url": f"https://www.amazon.es/dp/{asin}", "price": "19,99 €"}


def fake_scrape(counts):
    """A scrape_fn writing `counts[list_key]` items; None means the section failed."""
    def _scrape(out_dir):
        produced = {}
        for list_key, count in counts.items():
            if count is None:
                continue
            path = os.path.join(out_dir, FILENAMES[list_key])
            with open(path, "w", encoding="utf-8") as handle:
                json.dump([product_json(list_key, i) for i in range(count)], handle)
            produced[list_key] = path
        return produced
    return _scrape


def silent(*args, **kwargs):
    pass


def snapshot_catalog(session):
    products = sorted(tuple(row) for row in session.exec(
        select(Product.id, Product.title, Product.is_active, Product.updated_at)).all())
    lists = sorted(tuple(row) for row in session.exec(
        select(ProductList.product_id, ProductList.list_key, ProductList.rank)).all())
    return products, lists


def test_baseline_counts_reads_each_list(session, catalog_seed):
    """The health reference comes from the DB, so no new state is needed."""
    assert refresh_catalog.baseline_counts(session) == {"bestsellers": 2, "trends": 2}
