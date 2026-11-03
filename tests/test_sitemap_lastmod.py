"""Sitemap <lastmod>: real timestamps only, never fabricated dates.

The sitemap must emit <lastmod> solely where a reliable modification
timestamp exists (Product.updated_at / EditorialGateState.updated_at for
catalog surfaces) in W3C format, and must omit the element entirely for
URLs without one (home, /amigo-invisible, /blog and blog posts).
"""

import re
from datetime import datetime
from xml.etree import ElementTree

import pytest

import curation
from catalog import normalize_text
from models import EditorialDecision, EditorialGateState, Product, ProductList

W3C_LASTMOD_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _url_entries(response):
    """Map each <loc> URL to its <url> element."""
    root = ElementTree.fromstring(response.text)
    return {
        url.find("{*}loc").text: url
        for url in root.findall("{*}url")
    }


def _lastmod(url_element):
    node = url_element.find("{*}lastmod")
    return node.text if node is not None else None


@pytest.fixture(name="catalog_products")
def catalog_products_fixture(session):
    """Two products in one category plus one in another, with known updated_at."""

    def make(asin, category, slug, updated_at, is_active=True):
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
            is_active=is_active,
        )
        session.add(product)
        return product

    products = [
        make("A1", "Alimentación y bebidas", "alimentacion-y-bebidas",
             datetime(2026, 1, 1, 8, 0, 0)),
        make("A2", "Alimentación y bebidas", "alimentacion-y-bebidas",
             datetime(2026, 3, 5, 6, 7, 8)),
        make("B1", "Electrónica", "electronica", datetime(2026, 2, 1, 12, 0, 0)),
    ]
    session.add_all(products)
    session.commit()
    session.add_all([
        ProductList(product_id=products[0].id, list_key="bestsellers", rank=1),
        ProductList(product_id=products[1].id, list_key="bestsellers", rank=2),
        ProductList(product_id=products[2].id, list_key="trends", rank=1),
    ])
    session.commit()
    return products


def test_sitemap_lastmod_uses_w3c_datetime_format(client, catalog_products):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    for url in ElementTree.fromstring(response.text).findall("{*}url"):
        node = url.find("{*}lastmod")
        if node is not None:
            assert W3C_LASTMOD_RE.fullmatch(node.text), node.text


def test_category_landing_lastmod_is_newest_product_update(client, catalog_products):
    response = client.get("/sitemap.xml")
    entry = _url_entries(response)["https://regalame.app/ideas/alimentacion-y-bebidas"]
    assert _lastmod(entry) == "2026-03-05T06:07:08Z"


def test_aggregate_catalog_landings_lastmod_is_newest_product_update(client, catalog_products):
    response = client.get("/sitemap.xml")
    entries = _url_entries(response)
    for landing in ("/bestsellers", "/trends", "/most-desired"):
        assert _lastmod(entries[f"https://regalame.app{landing}"]) == "2026-03-05T06:07:08Z"


def test_inactive_product_does_not_touch_lastmod(client, session, catalog_products):
    inactive = Product(
        asin="X9",
        title="Retired product",
        title_normalized=normalize_text("Retired product"),
        image_url="img-x9.jpg",
        url="https://www.amazon.es/dp/X9",
        category="Alimentación y bebidas",
        category_slug="alimentacion-y-bebidas",
        price_numeric=10.0,
        price_raw="10 €",
        scraped_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 6, 1),
        is_active=False,
    )
    session.add(inactive)
    session.commit()

    response = client.get("/sitemap.xml")
    entries = _url_entries(response)
    # The inactive product is newer, but it is no longer part of the catalog.
    assert _lastmod(entries["https://regalame.app/ideas/alimentacion-y-bebidas"]) == \
        "2026-03-05T06:07:08Z"
    assert _lastmod(entries["https://regalame.app/bestsellers"]) == "2026-03-05T06:07:08Z"


def test_gate_state_update_floors_the_lastmod(client, session, catalog_products, monkeypatch):
    """Under enforce, a newer gate evaluation moves every surface's lastmod.

    Products need ``eligible`` decisions to stay visible under enforce, so the
    fixture seeds one per product; the gate floor (2026-04-01) is then newer
    than every Product.updated_at (max 2026-03-05) and must win.
    """
    monkeypatch.setattr(curation, "EDITORIAL_FILTER_MODE", "enforce")
    monkeypatch.setattr(curation, "EDITORIAL_POLICY_VERSION", "test")
    for product in catalog_products:
        session.add(EditorialDecision(product_id=product.id, state="eligible"))
    session.add(EditorialGateState(
        id=1,
        gate_passed=True,
        coverage_ratio=1.0,
        unknown_ratio=0.0,
        policy_version="test",
        model_id="test",
        evaluated_at=datetime(2026, 4, 1, 9, 30, 0),
        updated_at=datetime(2026, 4, 1, 9, 30, 0),
    ))
    session.commit()

    response = client.get("/sitemap.xml")
    entry = _url_entries(response)["https://regalame.app/ideas/alimentacion-y-bebidas"]
    assert _lastmod(entry) == "2026-04-01T09:30:00Z"


def test_no_lastmod_without_reliable_data(client):
    """Empty catalog: no lastmod anywhere, and no fabricated dates."""
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    root = ElementTree.fromstring(response.text)
    assert root.findall("{*}url/{*}lastmod") == []


def test_blog_urls_never_carry_lastmod(client, catalog_products):
    """Blog config has no publication dates, so no lastmod may be emitted."""
    response = client.get("/sitemap.xml")
    entries = _url_entries(response)
    for loc, url in entries.items():
        if loc.rstrip("/").endswith("/blog") or "/blog/" in loc:
            assert _lastmod(url) is None, loc


def test_home_and_amigo_invisible_never_carry_lastmod(client, catalog_products):
    response = client.get("/sitemap.xml")
    entries = _url_entries(response)
    assert _lastmod(entries["https://regalame.app/"]) is None
    assert _lastmod(entries["https://regalame.app/amigo-invisible"]) is None
