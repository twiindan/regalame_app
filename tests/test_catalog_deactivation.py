"""Deactivating the products that left every scraped list."""

from datetime import datetime

from sqlmodel import select

from catalog import deactivate_absent_products
from models import Product, ProductList, utcnow_naive


def make_product(session, asin, active=True, updated_at=None):
    product = Product(asin=asin, title=asin, title_normalized=asin.lower(),
                      image_url=None, url=f"https://www.amazon.es/dp/{asin}",
                      category="Varios", category_slug="varios",
                      price_numeric=None, price_raw="N/A",
                      scraped_at=datetime(2026, 1, 1), is_active=active,
                      updated_at=updated_at or utcnow_naive())
    session.add(product)
    session.commit()
    session.refresh(product)
    return product


def test_a_product_in_no_list_is_deactivated(session):
    ghost = make_product(session, "GHOSTGHOST")
    counted = make_product(session, "COUNTEDAAA")
    session.add(ProductList(product_id=counted.id, list_key="bestsellers", rank=1))
    session.commit()

    deactivated = deactivate_absent_products(session, list_keys=["bestsellers"])

    assert deactivated == 1
    session.refresh(ghost)
    session.refresh(counted)
    assert ghost.is_active is False
    assert counted.is_active is True


def test_a_product_in_another_list_survives(session):
    survivor = make_product(session, "SURVIVORAA")
    session.add(ProductList(product_id=survivor.id, list_key="trends", rank=1))
    session.commit()

    deactivated = deactivate_absent_products(session, list_keys=["bestsellers", "trends"])

    assert deactivated == 0
    session.refresh(survivor)
    assert survivor.is_active is True


def test_an_already_inactive_product_is_not_counted_twice(session):
    make_product(session, "SLEEPYAAAA", active=False)
    assert deactivate_absent_products(session, list_keys=["bestsellers"]) == 0


def test_deactivation_refreshes_updated_at(session):
    stamp = datetime(2026, 1, 1)
    ghost = make_product(session, "STAMPSTAMP", updated_at=stamp)

    deactivate_absent_products(session, list_keys=["bestsellers"])

    session.refresh(ghost)
    assert ghost.updated_at > stamp
