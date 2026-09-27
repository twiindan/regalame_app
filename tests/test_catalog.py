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


from catalog import _parse_price, extract_asin, normalize_text, slugify


def test_normalize_text_lowercases_and_strips_accents():
    assert normalize_text("Café") == "cafe"
    assert normalize_text("  Alimentación y Bebidas ") == "alimentacion y bebidas"
    assert normalize_text(None) == ""


def test_slugify_matches_existing_behavior():
    assert slugify("Hogar y cocina") == "hogar-y-cocina"
    assert slugify("Alimentación y bebidas") == "alimentacion-y-bebidas"


def test_extract_asin_from_dp_url():
    assert extract_asin("https://www.amazon.es/Lavazza-1kg/dp/B0049U0DMC/ref=zg_bs?psc=1") == "B0049U0DMC"


def test_extract_asin_from_gp_product_url():
    assert extract_asin("https://www.amazon.es/gp/product/B085LCQNZV?ref=x") == "B085LCQNZV"


def test_extract_asin_fallback_is_stable_and_distinct():
    a = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    b = extract_asin("https://www.amazon.es/algo-sin-asin/ref=x")
    c = extract_asin("https://www.amazon.es/otra-cosa/ref=x")
    assert a == b
    assert a.startswith("h")
    assert a != c


def test_parse_price_european_comma():
    assert _parse_price("19,99 €") == 19.99


def test_parse_price_eur_prefix():
    assert _parse_price("EUR 20.50") == 20.5


def test_parse_price_european_thousands():
    assert _parse_price("1.234,56") == 1234.56


def test_parse_price_non_numeric_returns_zero():
    assert _parse_price("N/A") == 0.0
    assert _parse_price(None) == 0.0
