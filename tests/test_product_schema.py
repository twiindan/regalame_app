"""Structured data (WU9): Product + Offer JSON-LD on category SEO landings.

Policy enforced here:
- Each ListItem of the existing CollectionPage ItemList wraps a Product via
  ``item`` (no duplicate ItemList markup).
- Offers are emitted only for products with a parsed price (``price_numeric``),
  always in EUR, pointing at the Amazon affiliate URL. A product without a
  price never gets an invented price.
- No ``aggregateRating`` and no ``review``: this catalog has none and inventing
  them is forbidden.
"""

import json

from bs4 import BeautifulSoup


def _json_ld(client, path):
    soup = BeautifulSoup(client.get(path).text, "html.parser")
    return [
        json.loads(script.string)
        for script in soup.find_all("script", attrs={"type": "application/ld+json"})
    ]


def _category_products(client, path):
    schemas = _json_ld(client, path)
    collection = next(s for s in schemas if s["@type"] == "CollectionPage")
    assert collection["mainEntity"]["@type"] == "ItemList"
    list_items = collection["mainEntity"]["itemListElement"]
    assert list_items
    return [li["item"] for li in list_items]


def test_list_items_wrap_products_without_duplicating_item_list(client, catalog_seed):
    schemas = _json_ld(client, "/ideas/alimentacion-y-bebidas")
    item_lists = [
        s for s in schemas
        if s.get("@type") == "ItemList"
        or isinstance(s.get("mainEntity"), dict)
        and s["mainEntity"].get("@type") == "ItemList"
    ]
    assert len(item_lists) == 1
    collection = next(s for s in schemas if s["@type"] == "CollectionPage")
    list_items = collection["mainEntity"]["itemListElement"]
    assert [li["@type"] for li in list_items] == ["ListItem", "ListItem"]
    assert [li["position"] for li in list_items] == [1, 2]
    for li in list_items:
        assert li["item"]["@type"] == "Product"
        assert li["name"] == li["item"]["name"]


def test_product_schema_matches_seeded_products(client, catalog_seed):
    products = _category_products(client, "/ideas/alimentacion-y-bebidas")
    by_name = {p["name"]: p for p in products}
    assert set(by_name) == {"Café molido", "Cafetera express"}
    cafe = by_name["Café molido"]
    assert cafe["image"] == "img-a1.jpg"


def test_priced_products_emit_offer_with_price_and_eur(client, catalog_seed):
    products = _category_products(client, "/ideas/alimentacion-y-bebidas")
    offers = {p["name"]: p["offers"] for p in products}
    assert offers["Café molido"] == {
        "@type": "Offer",
        "price": 10.0,
        "priceCurrency": "EUR",
        "url": "https://www.amazon.es/dp/A1",
    }
    assert offers["Cafetera express"]["price"] == 100.0
    assert offers["Cafetera express"]["priceCurrency"] == "EUR"


def test_product_without_price_gets_no_offers_and_no_invented_price(client, catalog_seed):
    products = _category_products(client, "/ideas/electronica")
    assert [p["name"] for p in products] == ["Auriculares bluetooth"]
    product = products[0]
    assert "offers" not in product
    assert "price" not in json.dumps(product)


def test_image_is_omitted_when_missing(client, catalog_seed, session):
    from datetime import datetime

    from catalog import normalize_text
    from models import Product, ProductList

    product = Product(
        asin="C1",
        title="Vino tinto",
        title_normalized=normalize_text("Vino tinto"),
        image_url=None,
        url="https://www.amazon.es/dp/C1",
        category="Alimentación y bebidas",
        category_slug="alimentacion-y-bebidas",
        price_numeric=7.5,
        price_raw="7.5 €",
        scraped_at=datetime(2026, 2, 1),
        updated_at=datetime(2026, 2, 1),
    )
    session.add(product)
    session.flush()
    session.add(ProductList(product_id=product.id, list_key="bestsellers", rank=3))
    session.commit()

    products = _category_products(client, "/ideas/alimentacion-y-bebidas")
    wine = next(p for p in products if p["name"] == "Vino tinto")
    assert "image" not in wine
    assert wine["offers"]["price"] == 7.5


def test_product_schema_never_declares_ratings_or_reviews(client, catalog_seed):
    for path in ["/ideas/alimentacion-y-bebidas", "/ideas/electronica"]:
        products = _category_products(client, path)
        blob = json.dumps(products)
        assert "aggregateRating" not in blob
        assert "review" not in blob
