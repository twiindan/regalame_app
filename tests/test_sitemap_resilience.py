"""Sitemap resilience: /sitemap.xml must never 500 because of lastmod.

The sitemap is freshness-metadata plus URLs. A failing <lastmod> query
(driver quirks, empty result shape, transient DB error) must degrade to a 200
response without <lastmod>, never lose URLs, and log the full traceback.
"""

from datetime import datetime
from xml.etree import ElementTree

import pytest

import main
from catalog import catalog_lastmod, category_lastmod, normalize_text
from models import Product


def _lastmod_map(response):
    """Map each <loc> URL to its <lastmod> text (None when absent)."""
    root = ElementTree.fromstring(response.text)
    return {
        url.find("{*}loc").text: (
            url.find("{*}lastmod").text if url.find("{*}lastmod") is not None else None
        )
        for url in root.findall("{*}url")
    }


@pytest.fixture(name="catalog_products")
def catalog_products_fixture(session):
    """Two products in one category plus one in another, with known updated_at."""

    def make(asin, category, slug, updated_at):
        product = Product(
            asin=asin,
            title=f"Product {asin}",
            title_normalized=normalize_text(f"Product {asin}"),
            image_url=f"img-{asin}.jpg",
            url=f"https://www.amazon.es/dp/{asin}",
            category=category,
            category_slug=slug,
            price_numeric=10.0,
            price_raw="10 €",
            scraped_at=datetime(2026, 1, 1),
            updated_at=updated_at,
            is_active=True,
        )
        session.add(product)
        return product

    session.add_all([
        make("A1", "Alimentación y bebidas", "alimentacion-y-bebidas",
             datetime(2026, 1, 1, 8, 0, 0)),
        make("A2", "Alimentación y bebidas", "alimentacion-y-bebidas",
             datetime(2026, 3, 5, 6, 7, 8)),
        make("B1", "Electrónica", "electronica", datetime(2026, 2, 1, 12, 0, 0)),
    ])
    session.commit()


@pytest.fixture(name="boom")
def boom_fixture(monkeypatch):
    """Make the aggregate lastmod query raise."""
    def raise_(session):
        raise RuntimeError("aggregate lastmod exploded")
    monkeypatch.setattr(main, "catalog_lastmod", raise_)
    return raise_


def test_sitemap_200_when_aggregate_lastmod_raises(client, catalog_products, boom):
    """Aggregate lastmod failure: 200, aggregate landings lose lastmod only."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    lastmods = _lastmod_map(response)
    for landing in ("/bestsellers", "/trends", "/most-desired"):
        assert lastmods[f"https://regalame.app{landing}"] is None
    # Every URL is still served.
    assert "https://regalame.app/" in lastmods
    assert "https://regalame.app/ideas/alimentacion-y-bebidas" in lastmods


def test_sitemap_keeps_all_urls_when_category_lastmod_raises(
    client, catalog_products, monkeypatch
):
    """Per-category lastmod failure: every landing URL stays in the XML."""
    def raise_(session, slug):
        raise RuntimeError(f"category lastmod exploded for {slug}")
    monkeypatch.setattr(main, "category_lastmod", raise_)

    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    body = response.text
    assert "/ideas/alimentacion-y-bebidas" in body
    assert "/ideas/electronica" in body
    # Aggregate landings still carry their (working) lastmod.
    assert "<lastmod>2026-03-05T06:07:08Z</lastmod>" in body


def test_lastmod_queries_on_empty_table_return_none_without_raising(session):
    """MAX over an empty table must yield None, not NoResultFound."""
    assert catalog_lastmod(session) is None
    assert category_lastmod(session, "alimentacion-y-bebidas") is None
