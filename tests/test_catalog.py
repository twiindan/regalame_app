from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from models import Product, ProductList


def test_product_and_productlist_roundtrip(session):
    product = Product(
        asin="B0049U0DMC",
        title="Lavazza Qualità Oro",
        title_normalized="lavazza qualita oro",
        image_url="https://img.example/1.jpg",
        url="https://www.amazon.es/dp/B0049U0DMC",
        category="Alimentación y bebidas",
        category_slug="alimentacion-y-bebidas",
        price_numeric=25.69,
        price_raw="25,69 €",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    link = ProductList(product_id=product.id, list_key="bestsellers", rank=1)
    session.add(link)
    session.commit()

    stored = session.exec(select(Product).where(Product.asin == "B0049U0DMC")).first()
    assert stored is not None
    assert stored.title_normalized == "lavazza qualita oro"
    assert stored.price_numeric == 25.69
    assert stored.is_active is True
    assert stored.updated_at is not None

    stored_link = session.exec(select(ProductList).where(ProductList.list_key == "bestsellers")).first()
    assert stored_link is not None
    assert stored_link.product_id == product.id
    assert stored_link.rank == 1


def test_productlist_unique_per_product_and_list(session):
    product = Product(
        asin="X1",
        title="T",
        title_normalized="t",
        url="https://www.amazon.es/dp/X1",
        category="Varios",
        category_slug="varios",
        scraped_at=datetime(2026, 9, 1),
    )
    session.add(product)
    session.commit()
    session.refresh(product)

    session.add(ProductList(product_id=product.id, list_key="trends", rank=1))
    session.commit()
    session.add(ProductList(product_id=product.id, list_key="trends", rank=2))
    with pytest.raises(IntegrityError):
        session.commit()
